#include <iomanip>
#include <iostream>
#include <memory>
#include <thread>
#include <libcamera/libcamera.h>
#include <sys/mman.h>

using namespace libcamera;
using namespace std::chrono_literals;

static std::shared_ptr<Camera> camera;
static uint frame_count = 0;
static StreamConfiguration *streamConfig;

int findMedianOrangePixel(uint8_t *data, int width, int height, int &medianX, int &medianY) {
    std::vector<int> orangeX, orangeY;
    int res = -1;
    const int blockSize = 16 * 16;  // Each block contains 16 cells, each with 16 pixels
    const int cellSize = 16;  // Each cell contains 16 pixels in a checker pattern
    
    for (int blockY = 0; blockY < height; blockY += 16 * 2) {  // Skip alternate blocks
        for (int blockX = 0; blockX < width; blockX += 16 * 2) {
            for (int cellY = 0; cellY < 16; cellY += 2) {  // Checker pattern in cells
                for (int cellX = 0; cellX < 16; cellX += 2) {
                    int pixelX = blockX + cellX;
                    int pixelY = blockY + cellY;
                    if (pixelX < width && pixelY < height) {
                        int index = pixelY * width + pixelX;
                        int pixelValue = data[index];
                        if (pixelValue > 100 && pixelValue < 255) {  // Simple orange threshold
                            orangeX.push_back(pixelX);
                            orangeY.push_back(pixelY);
                            res = 1;
                        }
                    }
                }
            }
        }
    }
    
    if (orangeX.empty()) return -1;  // No orange pixels found
    std::nth_element(orangeX.begin(), orangeX.begin() + orangeX.size() / 2, orangeX.end());
    std::nth_element(orangeY.begin(), orangeY.begin() + orangeY.size() / 2, orangeY.end());
    medianX = orangeX[orangeX.size() / 2];
    medianY = orangeY[orangeY.size() / 2];
    return res;
}

void requestComplete(Request *request) {
    frame_count++;
    const int DARK_THRESHOLD = 10;
    const float DARK_RATIO = 0.9;
    if (request->status() == Request::RequestCancelled)
        return;

    const std::map<const Stream *, FrameBuffer *> &buffers = request->buffers();
    for (auto bufferPair : buffers) {
        int dark_pixels = 0;
        int total_pixels = 0;
        FrameBuffer *buffer = bufferPair.second;
        const FrameMetadata &metadata = buffer->metadata();
        
        int fd = buffer->planes()[0].fd.get();
        void *mapped_data = mmap(NULL, buffer->planes()[0].length, PROT_READ, MAP_SHARED, fd, 0);
        if (mapped_data == MAP_FAILED) {
            std::cerr << "Failed to map memory" << std::endl;
            return;
        }

        uint8_t *data = static_cast<uint8_t *>(mapped_data);
        for (unsigned int i = 0; i < buffer->planes()[0].length; ++i) {
            if (data[i] < DARK_THRESHOLD) {
                dark_pixels++;
            }
            total_pixels++;
        }
        

        if (frame_count % 100 == 0) {
            std::cout << "Frame: " << frame_count << std::endl;
        } 
        
        int medianX, medianY;
        int medianOrange = findMedianOrangePixel(static_cast<uint8_t *>(mapped_data), streamConfig->size.width, streamConfig->size.height, medianX, medianY);
        if (medianOrange != -1) {
            std::cout << "Median Orange Position: (" << medianX << ", " << medianY << ")" << std::endl;
        } else {
            std::cout << "No orange pixels detected." << std::endl;
        }
        std::cout << std::endl;
        munmap(mapped_data, buffer->planes()[0].length);
    }
    request->reuse(Request::ReuseBuffers);
    camera->queueRequest(request);
}

int main() {
    std::unique_ptr<CameraManager> cm = std::make_unique<CameraManager>();
    cm->start();

    auto cameras = cm->cameras();
    if (cameras.empty()) {
        std::cout << "No cameras were identified on the system." << std::endl;
        cm->stop();
        return EXIT_FAILURE;
    }

    std::string cameraId = cameras[0]->id();
    camera = cm->get(cameraId);
    camera->acquire();

    
    std::unique_ptr<CameraConfiguration> config = camera->generateConfiguration({ StreamRole::Viewfinder });
    streamConfig = &config->at(0);
    if (!streamConfig) {
        std::cerr << "Failed to get stream configuration" << std::endl;
        return EXIT_FAILURE;
    }
    streamConfig->size.width = 224;
    streamConfig->size.height = 96;
    config->validate();
    camera->configure(config.get());

    FrameBufferAllocator *allocator = new FrameBufferAllocator(camera);
    for (StreamConfiguration &cfg : *config) {
        int ret = allocator->allocate(cfg.stream());
        if (ret < 0) {
            std::cerr << "Can't allocate buffers" << std::endl;
            return -ENOMEM;
        }
        size_t bufferCount = 8;
        size_t allocated = allocator->buffers(cfg.stream()).size();
        std::cout << "Allocated " << allocated << " buffers for stream" << std::endl;
    }

    Stream *stream = streamConfig->stream();
    const std::vector<std::unique_ptr<FrameBuffer>> &buffers = allocator->buffers(stream);
    std::vector<std::unique_ptr<Request>> requests;

    for (unsigned int i = 0; i < buffers.size(); ++i) {
        std::unique_ptr<Request> request = camera->createRequest();
        if (!request) {
            std::cerr << "Can't create request" << std::endl;
            return -ENOMEM;
        }
        const std::unique_ptr<FrameBuffer> &buffer = buffers[i];
        int ret = request->addBuffer(stream, buffer.get());
        if (ret < 0) {
            std::cerr << "Can't set buffer for request" << std::endl;
            return ret;
        }
        requests.push_back(std::move(request));
    }

    camera->requestCompleted.connect(requestComplete);
    auto start_time = std::chrono::high_resolution_clock::now();
    std::unique_ptr<libcamera::ControlList> camcontrols = std::make_unique<libcamera::ControlList>();
    camcontrols->set(controls::FrameDurationLimits, libcamera::Span<const std::int64_t, 2>({100, 4000}));
    camera->start(camcontrols.get());
    for (std::unique_ptr<Request> &request : requests)
        camera->queueRequest(request.get());

    std::this_thread::sleep_for(30000ms);
    auto end_time = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double> elapsed = end_time - start_time;
    double fps = frame_count / elapsed.count();
    std::cout << "FPS: " << fps << std::endl;

    camera->stop();
    allocator->free(stream);
    delete allocator;
    camera->release();
    camera.reset();
    cm->stop();

    return 0;
}

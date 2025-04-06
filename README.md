Below is the final README content in Markdown format. You can save this as `README.md` in your repository.

---

# High-Speed Insect Tracking on Raspberry Pi 5

This project evaluates the feasibility of tracking small insects—such as Colorado beetles—at over 500 frames per second (FPS) using a Raspberry Pi 5 with a global shutter camera. The ultimate goal is to develop a laser-based system capable of detecting and neutralizing pests with high precision, as part of photonic insecticides developements.

## Project Overview

The objectives of this project are to:

- **Capture** high-speed video (500+ FPS) using a Raspberry Pi 5 and a global shutter camera.
- **Process** the incoming video stream in real time with a lightweight program that:
  - Tracks insects in the field.
  - Computes positional errors relative to the center of the viewport.
  - Outputs correction PID commands to servos that steer a mirror, keeping the insect centered.
- **Record** the modified video stream to disk for further analysis.
- **Assess** whether high-contrast insects (e.g., Colorado beetles -- oragne thorax on green leafy background) can be reliably tracked as a precursor for a laser-based pest control system.

## Hardware Setup

1. **Raspberry Pi 5 (8 GB, ARM A76 @ 2.4 GHz)**  
   The main computing platform handling both video capture and real-time processing.

2. **Raspberry Pi Global Shutter Camera**  
   This camera, available from Kiwi Electronics (see [Raspberry Pi Global Shutter Camera with C-mount](https://www.kiwi-electronics.com/en/raspberry-pi-global-shutter-camera-c-mount-11346?srsltid=AfmBOorjyt3xhTllkbBb9jNMj-0uA5owiSabHFzQiQZfjXykuc6Kj5gH)), ensures high-speed imaging with minimal motion blur—critical for capturing rapid insect movement.

3. **M12 Lens (25 mm, F11.0)**  
   A fixed-focal-length lens from Scorpion Vision, chosen for its compatibility with the global shutter camera and its ability to deliver detailed images at high frame rates.

4. **C/CS Mount to M12 Lens Adapter**  
   This adapter allows the M12 lens to be securely attached to the camera’s C-mount port.

5. **Video Output/Display Setup:**  
   - A mini HDMI to HDMI adapter connected to the Raspberry Pi.
   - An HDMI to USB‑C cable feeds the signal into an M1 MacBook.
   - OBS (Open Broadcaster Software) on the MacBook captures the USB‑C input, providing real-time viewing of the Raspberry Pi’s desktop.

6. **Input Devices:**  
   A budget-friendly mouse and keyboard attached to the Raspberry Pi allow for direct control and configuration.

7. **Power Supply:**  
   The official Raspberry Pi power adapter is used to ensure stable power delivery, addressing issues experienced with alternative USB‑C power sources.

## Camera Configuration

Before capturing video, it is essential to configure the camera with all necessary parameters that cannot be set via code or the `rpicam-vid` command alone. This is achieved by running the `GScrop` command (from [this repository](https://gist.github.com/Hermann-SW/e6049fe1a24fc2b5a53c654e0e9f6b9c)), which uses `media-ctl` to properly configure the camera hardware settings (such as format and cropping).

**Verification Step:**  
After running `GScrop`, verify that the camera is correctly configured in the OS by executing:

    libcamera-hello --list-cameras

This command will list the cameras recognized by libcamera. Ensure that your global shutter camera appears with the expected settings before proceeding.

## Software Pipeline

1. **Camera Feed Acquisition**  
   The video feed is captured using `rpicam-vid` and piped through custom tools. For example, the following command (executed in the terminal on the Raspberry Pi) captures video at 536 FPS:

   ```
   ./GScrop 224 96 536 32; rpicam-vid --no-raw --codec yuv420 --width 224 --height 96 --denoise cdn_off --framerate 536 -t 20000 -o - 2>/dev/null | ./sample_yuv_brightness 256 96 2>err | ffmpeg -f rawvideo -vcodec rawvideo -s 256x96 -r 536 -pix_fmt yuv420p -i - -c:v libx264 -preset slow -qp 0 -y tst.mp4 -loglevel quiet
   ```

   *Note:* Remove the `-n` flag from `rpicam-vid` if you want a live preview (at the cost of a lower frame rate).

2. **Real-Time Insect Tracking and Mirror Steering**  
   A lightweight processing program receives the piped YUV stream and performs:
   - Insect detection and tracking.
   - Calculation of positional error relative to the center of the viewport.
   - Generation of correction commands via a PID controller.
   - Output of these commands to servos controlling a mirror, ensuring that the insect remains centered in the frame.

3. **Modified Stream Output and Storage Optimization**  
   The processed video stream is encoded using FFmpeg (with lossless H.264 settings) and written to disk as `tst.mp4` for offline analysis. To minimize disk I/O latency and efficiently handle the high data rate, the output files are written to a RAM disk.

   **Setting Up a RAM Disk on Linux:**

   - **Create a Mount Point:**  
     Run:  
     `sudo mkdir /mnt/ramdisk`
   
   - **Mount a tmpfs Volume (e.g., 100 MB):**  
     Run:  
     `sudo mount -t tmpfs -o size=100M tmpfs /mnt/ramdisk`
   
   - **Direct Output to the RAM Disk:**  
     Modify your FFmpeg command to write the output file (e.g., `tst.mp4`) to `/mnt/ramdisk`.

   *Note:* Data stored on a RAM disk is volatile and will be lost upon shutdown. Be sure to copy your files to permanent storage after capture.

## Alignment Warning and YUV Padding Issue

When running a command such as:

    rpicam-vid --no-raw --codec yuv420 --width 224 --height 96 --denoise cdn_off --framerate 536 -t 1000 -o tst.yuv420

**Warning:**  
The Raspberry Pi 5 (unlike the Pi 4) prefers 64-byte alignment. To achieve 64-byte alignment in the U and V planes, the Y plane is padded to 128-byte alignment. As a result, each row of the Y component contains 384 bytes instead of the expected 288 bytes. This extra padding is important to consider when processing the YUV data.

For example, to extract the first frame from the YUV file, use:

    (echo -e "P5\n256 96\n255\n" && head --bytes $((256*96)) tst.yuv420) > frame.pgm

And display it with:

    pgmtoppm < frame.pgm | pnmtopng > frame.pgm.png

Additional details and discussion about this issue are available on our project forum.

## Command Breakdown

The complete command for video capture and processing is split into several components:

1. **Camera Configuration:**  
   `./GScrop 224 96 536 32;`  
   - Runs the `GScrop` utility to configure the camera via `media-ctl` with parameters such as resolution and frame rate.
   - The semicolon (`;`) separates this configuration step from subsequent commands.

2. **Video Capture:**  
   `rpicam-vid --no-raw --codec yuv420 --width 224 --height 96 --denoise cdn_off --framerate 536 -t 20000 -o - 2>/dev/null |`  
   - Captures video using `rpicam-vid` at a resolution of 224×96 pixels with YUV420 encoding and a frame rate of 536 FPS.
   - Disables raw file output (`--no-raw`) and denoising (`--denoise cdn_off`).
   - Captures for 20 seconds (`-t 20000`) and outputs the stream to standard output.
   - Redirects error messages to `/dev/null`.
   - Pipes the output to the next stage.

3. **Brightness Processing:**  
   `./sample_yuv_brightness 256 96 2>err |`  
   - Processes the YUV stream (e.g., adjusts brightness) and resizes it to 256×96 pixels.
   - Redirects error output to a file named “err.”
   - Pipes the processed stream to the final encoding stage.

4. **Video Encoding and Storage:**  
   `ffmpeg -f rawvideo -vcodec rawvideo -s 256x96 -r 536 -pix_fmt yuv420p -i - -c:v libx264 -preset slow -qp 0 -y tst.mp4 -loglevel quiet`  
   - Informs FFmpeg that the input is raw video with a resolution of 256×96 pixels and 536 FPS, using the YUV420p pixel format.
   - Reads input from standard input (`-i -`) and encodes the output using the H.264 codec (`libx264`) with lossless settings (`-qp 0`).
   - Overwrites the file `tst.mp4` (`-y`) and suppresses log output (`-loglevel quiet`).

## Project Goals

- **High Frame-Rate Capture:**  
  Validate that the Raspberry Pi 5 and global shutter camera can reliably capture video at 500+ FPS without significant frame drops.

- **Real-Time Processing:**  
  Ensure that the entire pipeline—including insect tracking and mirror steering—can handle the high data rate with minimal latency.

- **Insect Tracking Feasibility:**  
  Analyze recorded video and PID outputs to determine if small, fast-moving insects (like Colorado beetles) can be accurately detected and kept centered in the viewport.

- **Laser Integration Potential:**  
  Evaluate whether the system’s precision and response time are sufficient for eventual integration with a laser module to target insects.

## Future Work

- **Advanced Image Analysis:**  
  Develop and test more sophisticated tracking algorithms (e.g., background subtraction, feature detection) to improve detection accuracy.

- **Laser Module Integration:**  
  Investigate real-time aiming and firing mechanisms to neutralize insects based on the tracking data.

- **Hardware Refinements:**  
  Experiment with different lenses or camera modules to optimize image clarity, field of view, and overall performance at extreme frame rates.

## References

Sample yuv brightness : https://github.com/Hermann-SW2/userland/blob/master/host_applications/linux/apps/hello_pi/i420toh264/sample_yuv_brightness.c

GScrop: https://gist.github.com/Hermann-SW/e6049fe1a24fc2b5a53c654e0e9f6b9c

Trouble shooting (details about YUV padding issue): https://forums.raspberrypi.com/viewtopic.php?p=2305225#p2305225

## Special thanks

This project would not have been possible without the vital help of
stamm wilbrandt (https://stamm-wilbrandt.de/en/), who supplied the key commands and laid the groundwork that allows this project to function, in his many years of contributions.

## Contributing

Contributions, suggestions, and improvements are welcome. Please open an issue or submit a pull request with your ideas and enhancements.

## License

This project is licensed under the [MIT License](LICENSE).

## Contact

For questions or to contribute, please contact:  
- **Name:** [Your Name]  
- **Email:** [your.email@example.com]

---

*Note: This README is a preliminary draft. More details—such as exact OS configurations, performance benchmarks, and final tracking outcomes—will be added as the project evolves.*

---

You now have a comprehensive README that explains the hardware, camera configuration (including the media-ctl setup with GScrop), the complete command pipeline (with breakdown), storage optimizations using a RAM disk, and troubleshooting details regarding YUV row padding.

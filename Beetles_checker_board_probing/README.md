Insect Feature Extraction and Tracking
The tool simulates a low-resolution camera by transforming a selected region of an image into a 224×96 low-res image. It then performs color-based cell classification to detect the beetle’s thorax—distinctive for its orange color compared to the body’s white stripes on a black background. For this classification, the image is divided into blocks of 16×16 pixels. Each block is further subdivided into a 4×4 grid of cells (each cell being 4×4 pixels). Within each cell, only half of the pixels (those where the sum of the cell coordinates is even) are examined, which greatly speeds up processing. For each of these selected pixels, the RGB values are reduced in resolution (by dividing by 16) and then compared against predefined criteria to count pixels that match orange, white, or darker orange color profiles. If a cell has at least three pixels that meet a specific criterion, its center is recorded in the corresponding list (e.g., orange_cells). The tool then draws a triangle on the processed image in an attempt to estimate the beetle’s head location based on the relative positions of the orange thorax and the white-striped body. Additionally, an ORB feature extraction component is included to compare consecutive frames and track movement, although this part is still under development and does not yet produce reliable results.
Below is the code snippet that implements the color-based cell classification:

for by in range(0, 96, 16):
    for bx in range(0, 224, 16):
        for cy in range(4):
            for cx in range(4):
                if (cx + cy) % 2 == 0:
                    x, y = bx + cx * 4, by + cy * 4
                    orange_cnt = white_cnt = darker_orange_cnt = 0
                    for py in range(4):
                        for px in range(4):
                            if (px + py) % 2 == 0:
                                r_val, g_val, b_val = pixels[x + px, y + py]
                                qr, qg, qb = r_val // 16, g_val // 16, b_val // 16
                                if qr >= 12 and 4 <= qg <= 11 and qb <= 4:
                                    orange_cnt += 1
                                if qr >= 13 and qg >= 13 and qb >= 13:
                                    white_cnt += 1
                                if 6 <= qr <= 12 and 3 <= qg <= 8 and qb <= 3:
                                    darker_orange_cnt += 1
                    if orange_cnt >= 3:
                        orange_cells.append((x + 2, y + 2))
                    if white_cnt >= 3:
                        white_cells.append((x + 2, y + 2))
                    if darker_orange_cnt >= 3:
                        darker_orange_cells.append((x + 2, y + 2))


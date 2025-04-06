import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import cv2

class App:
    def __init__(self, master):
        self.master = master
        self.master.title("Triangle Search with ORB Features & Thresholding")

        self.image = None
        self.photo = None
        self.result_photo = None
        self.orb_photo = None
        self.rect = None

        tk.Button(master, text="Open Image", command=self.open_image).pack(pady=10)

        self.paned = tk.PanedWindow(master, orient=tk.HORIZONTAL)
        self.paned.pack(fill="both", expand=True)

        input_frame = tk.Frame(self.paned)
        self.paned.add(input_frame)

        self.canvas = tk.Canvas(input_frame, cursor="cross")
        self.canvas.grid(row=0, column=0, sticky="nsew")

        v_scroll = tk.Scrollbar(input_frame, orient="vertical", command=self.canvas.yview)
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll = tk.Scrollbar(input_frame, orient="horizontal", command=self.canvas.xview)
        h_scroll.grid(row=1, column=0, sticky="ew")

        self.canvas.configure(xscrollcommand=h_scroll.set, yscrollcommand=v_scroll.set)
        input_frame.rowconfigure(0, weight=1)
        input_frame.columnconfigure(0, weight=1)

        self.output_canvas = tk.Canvas(self.paned, width=224*3, height=96*3, bg="gray")
        self.paned.add(self.output_canvas)

        # New canvas for displaying the ORB features subregion
        self.orb_canvas = tk.Canvas(master, width=30*3, height=30*3, bg="gray")
        self.orb_canvas.pack(pady=10)

        self.canvas.bind("<ButtonPress-1>", self.start_rect)
        self.canvas.bind("<B1-Motion>", self.move_rect)
        self.canvas_img = None

    def open_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if path:
            self.image = Image.open(path)
            self.photo = ImageTk.PhotoImage(self.image)
            self.canvas.config(scrollregion=(0, 0, self.image.width, self.image.height), width=600, height=400)
            self.canvas_img = self.canvas.create_image(0, 0, image=self.photo, anchor="nw")

    def start_rect(self, event):
        self.x0, self.y0 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.x0, self.y0, self.x0, self.y0, outline="red")

    def move_rect(self, event):
        x1, y1 = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        self.canvas.coords(self.rect, self.x0, self.y0, x1, y1)
        self.process_selection(int(min(self.x0, x1)), int(min(self.y0, y1)),
                               int(max(self.x0, x1)), int(max(self.y0, y1)))

    def process_selection(self, l, u, r, d):
        if r - l < 4 or d - u < 4:
            return
        # Crop and resize to simulate low-res input (224x96)
        region = self.image.crop((l, u, r, d)).resize((224, 96), Image.NEAREST)
        # Make a clean copy for ORB feature extraction (before any drawing)
        region_clean = region.copy()
        pixels = region.load()
        orange_cells, white_cells, darker_orange_cells = [], [], []

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

        draw = ImageDraw.Draw(region)
        if orange_cells and white_cells:
            orange_center = np.median(np.array(orange_cells), axis=0)
            white_coords = np.array(white_cells)
            dists = np.linalg.norm(white_coords - orange_center, axis=1)
            close_white = white_coords[dists <= 40]

            if len(close_white) > 0:
                white_center = np.median(close_white, axis=0)
                direction = orange_center - white_center
                perp = np.array([-direction[1], direction[0]])
                if np.linalg.norm(perp) != 0:
                    perp = perp / np.linalg.norm(perp) * 40
                else:
                    perp = np.array([0, 0])
                deep_direction = direction * 3

                triangle = [tuple(white_center),
                            tuple(orange_center + deep_direction + perp),
                            tuple(orange_center + deep_direction - perp)]
                draw.polygon(triangle, outline="green")

                selected_cells = [cell for cell in darker_orange_cells if self.point_in_triangle(cell, triangle)]
                if selected_cells:
                    darker_median = np.median(selected_cells, axis=0)
                    draw.ellipse([darker_median[0] - 4, darker_median[1] - 4,
                                  darker_median[0] + 4, darker_median[1] + 4], fill="green")

                draw.ellipse([white_center[0] - 3, white_center[1] - 3,
                              white_center[0] + 3, white_center[1] + 3], fill="red")

            # Draw blue dot at the median of orange cells
            draw.ellipse([orange_center[0] - 3, orange_center[1] - 3,
                          orange_center[0] + 3, orange_center[1] + 3], fill="blue")

            # --- ORB Feature Extraction from a Clean Region ---
            blue_center = (int(orange_center[0]), int(orange_center[1]))
            left_bound = blue_center[0] - 15
            upper_bound = blue_center[1] - 15
            right_bound = blue_center[0] + 15
            lower_bound = blue_center[1] + 15

            # Ensure the 30x30 area is within the region (224x96)
            if left_bound < 0:
                left_bound = 0
                right_bound = left_bound + 30
            if upper_bound < 0:
                upper_bound = 0
                lower_bound = upper_bound + 30
            if right_bound > 224:
                right_bound = 224
                left_bound = right_bound - 30
            if lower_bound > 96:
                lower_bound = 96
                upper_bound = lower_bound - 30

            # Use the clean, unmodified region for ORB extraction
            subregion = region_clean.crop((left_bound, upper_bound, right_bound, lower_bound))
            sub_cv = np.array(subregion.convert("RGB"))
            sub_cv = sub_cv[:, :, ::-1]  # Convert from RGB to BGR

            # Convert to grayscale and apply thresholding to separate dark spots from orange background.
            gray = cv2.cvtColor(sub_cv, cv2.COLOR_BGR2GRAY)
            # Threshold: pixels darker than 150 become white (foreground), the rest become black.
            _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY_INV)

            # Use ORB on the thresholded image; lower fastThreshold to capture more features.
            orb = cv2.ORB_create(nfeatures=1000, fastThreshold=5)
            keypoints, descriptors = orb.detectAndCompute(thresh, None)
            
            # Print the number of keypoints and their average quality (response)
            print("Number of keypoints:", len(keypoints))
            if keypoints:
                avg_quality = sum(kp.response for kp in keypoints) / len(keypoints)
                print("Average keypoint quality:", avg_quality)

            # Draw keypoints on the thresholded image for visualization.
            kp_image = cv2.drawKeypoints(thresh, keypoints, None, color=(0, 255, 0), flags=0)
            kp_image = cv2.cvtColor(kp_image, cv2.COLOR_BGR2RGB)
            orb_img = Image.fromarray(kp_image)
            orb_img = orb_img.resize((30 * 3, 30 * 3), Image.NEAREST)
            self.orb_photo = ImageTk.PhotoImage(orb_img)
            self.orb_canvas.create_image(0, 0, image=self.orb_photo, anchor="nw")

        region_resized = region.resize((224 * 3, 96 * 3), Image.NEAREST)
        self.result_photo = ImageTk.PhotoImage(region_resized)
        self.output_canvas.create_image(0, 0, image=self.result_photo, anchor="nw")

    def point_in_triangle(self, pt, tri):
        def sign(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        b1 = sign(pt, tri[0], tri[1]) < 0
        b2 = sign(pt, tri[1], tri[2]) < 0
        b3 = sign(pt, tri[2], tri[0]) < 0
        return (b1 == b2) and (b2 == b3)

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()


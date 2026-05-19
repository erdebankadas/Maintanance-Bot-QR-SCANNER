import pyodbc
import tkinter as tk
from tkinter import ttk, messagebox
import qrcode
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import os
from datetime import datetime
import pytz

class QRCodeGeneratorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Industrial QR Generator")
        self.root.geometry("400x300")

        # Database Mapping
        self.db_map = {
            'SHJM': 'Smart_Eye_Jute_STIL_Hastings_Live',
            'MIJM': 'Smart_Eye_Jute_STIL_India_Live',
            'SGJM': 'Smart_Eye_Jute_STIL_Gondalpara_Live',
            'SSKT': 'Smart_Eye_Jute_STIL_Shaktigarh_Live'
        }

        # UI Layout
        tk.Label(root, text="Select Manufacturing Unit:", font=('Arial', 10, 'bold')).pack(pady=10)
        
        self.unit_dropdown = ttk.Combobox(root, values=list(self.db_map.keys()), state="readonly")
        self.unit_dropdown.pack(pady=5)
        self.unit_dropdown.set('SHJM')

        self.btn_generate = tk.Button(
            root,
            text="Connect & Generate PDF",
            command=self.process_data,
            bg="#1a1a1a",
            fg="white",
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=10
        )
        self.btn_generate.pack(pady=40)

    def create_custom_qr(self, scan_data, center_text):
        # Use High Error Correction
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )

        qr.add_data(scan_data)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white").convert('RGB')

        draw = ImageDraw.Draw(img)
        width, height = img.size

        # Center Box
        box_width = 110
        box_height = 45

        pos_x = (width - box_width) // 2
        pos_y = (height - box_height) // 2

        # Draw white box
        draw.rectangle(
            [pos_x, pos_y, pos_x + box_width, pos_y + box_height],
            fill="white",
            outline="black"
        )

        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()

        # Text center
        text_bbox = draw.textbbox((0, 0), center_text, font=font)

        text_w = text_bbox[2] - text_bbox[0]
        text_h = text_bbox[3] - text_bbox[1]

        draw.text(
            (
                pos_x + (box_width - text_w) / 2,
                pos_y + (box_height - text_h) / 2 - 2
            ),
            center_text,
            fill="black",
            font=font
        )

        return img

    def process_data(self):
        unit = self.unit_dropdown.get()
        db_name = self.db_map.get(unit)

        server = r'202.140.137.225\STILDB,8181'
        username = 'ERP'
        password = 'ERP#SFactor'

        conn_str = (
            f'DRIVER={{SQL Server}};'
            f'SERVER={server};'
            f'DATABASE={db_name};'
            f'UID={username};'
            f'PWD={password}'
        )

        try:
            conn = pyodbc.connect(conn_str, autocommit=True)
            cursor = conn.cursor()

            # Fetch Data
            cursor.execute("""
                SELECT CODE, DEPT, CLD_McDesc
                FROM OMCH
                WHERE ACTIVE = 'Y'
            """)

            rows = cursor.fetchall()

            if rows:
                self.generate_pdf(rows, unit)
                messagebox.showinfo(
                    "Success",
                    f"PDF Generated successfully for {unit}!"
                )
            else:
                messagebox.showwarning(
                    "No Data",
                    "No active records found in OMCH."
                )

            conn.close()

        except Exception as e:
            messagebox.showerror(
                "Database Connection Error",
                f"Could not connect:\n{str(e)}"
            )

    def generate_pdf(self, data_rows, unit_name):
        pdf_file = f"QR_Labels_{unit_name}.pdf"

        c = canvas.Canvas(pdf_file, pagesize=A4)

        width, height = A4

        # Grid Configuration
        cols = 3
        rows_per_page = 4

        x_margin = 50
        y_margin = 60

        qr_size = 145

        x_space = (
            (width - (2 * x_margin) - (cols * qr_size))
            / (cols - 1)
        )

        y_space = (
            (height - (2 * y_margin) - (rows_per_page * qr_size))
            / (rows_per_page - 1)
        )

        for i, record in enumerate(data_rows):

            code = str(record[0]).strip()
            dept = str(record[1]).strip()
            CLD_McDesc = str(record[2]).strip()

            # Indian Date & Time
            india_tz = pytz.timezone('Asia/Kolkata')

            generated_time = datetime.now(india_tz).strftime(
                "%d-%m-%Y %I:%M:%S %p"
            )

            # QR Scan Content
            scan_content = (
                f"MACHINE NO: {code}\n"
                f"DEPT: {dept}\n"
                f"LOCATION: {unit_name}\n"
                f"MC DESC : {CLD_McDesc}\n"
                f"GENERATED DATE & TIME : {generated_time}"
            )

            # Generate QR
            qr_img = self.create_custom_qr(scan_content, code)

            temp_path = f"temp_{i}.png"

            qr_img.save(temp_path)

            # Grid Position
            page_pos = i % 12

            col = page_pos % cols
            row = page_pos // cols

            x = x_margin + col * (qr_size + x_space)

            y = (
                height
                - y_margin
                - (row + 1) * qr_size
                - (row * y_space)
            )

            # Place QR
            c.drawImage(
                temp_path,
                x,
                y,
                width=qr_size,
                height=qr_size
            )

            # Remove Temp File
            os.remove(temp_path)

            # New Page after 12 QR
            if (i + 1) % 12 == 0 and (i + 1) < len(data_rows):
                c.showPage()

        c.save()

if __name__ == "__main__":
    root = tk.Tk()

    app = QRCodeGeneratorApp(root)

    root.mainloop()
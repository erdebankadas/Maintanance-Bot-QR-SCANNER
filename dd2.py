import pyodbc
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
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
        self.root.geometry("500x550")

        # ================= DATABASE MAP =================

        self.db_map = {
            'SHJM': 'Smart_Eye_Jute_STIL_Hastings_Live',
            'MIJM': 'Smart_Eye_Jute_STIL_India_Live',
            'SGJM': 'Smart_Eye_Jute_STIL_Gondalpara_Live',
            'SSKT': 'Smart_Eye_Jute_STIL_Shaktigarh_Live'
        }

        self.conn = None
        self.cursor = None

        # ================= UI =================

        tk.Label(
            root,
            text="Select Manufacturing Unit:",
            font=('Arial', 10, 'bold')
        ).pack(pady=10)

        self.unit_dropdown = ttk.Combobox(
            root,
            values=list(self.db_map.keys()),
            state="readonly",
            width=35
        )

        self.unit_dropdown.pack(pady=5)
        self.unit_dropdown.set('SHJM')

        # ================= CONNECT BUTTON =================

        self.connect_btn = tk.Button(
            root,
            text="Connect Server",
            command=self.connect_server,
            bg="green",
            fg="white",
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=8
        )

        self.connect_btn.pack(pady=10)

        # ================= OPTION LABEL =================

        tk.Label(
            root,
            text="Select QR Generation Type:",
            font=('Arial', 10, 'bold')
        ).pack(pady=10)

        # ================= OPTION DROPDOWN =================

        self.option_dropdown = ttk.Combobox(
            root,
            state="readonly",
            width=35,
            values=[
                "All At A Glance",
                "Only Mill Side",
                "Only Factory Side",
                "Particular Department",
                "Any Particular Machine"
            ]
        )

        self.option_dropdown.pack(pady=5)

        self.option_dropdown.bind(
            "<<ComboboxSelected>>",
            self.option_changed
        )

        # ================= DYNAMIC FRAME =================

        self.dynamic_frame = tk.Frame(root)
        self.dynamic_frame.pack(pady=10)

        # ================= DEPARTMENT DROPDOWN =================

        self.dept_dropdown = ttk.Combobox(
            self.dynamic_frame,
            state="readonly",
            width=30
        )

        # ================= MACHINE ENTRY =================

        self.machine_entry = tk.Entry(
            self.dynamic_frame,
            font=('Arial', 10),
            width=32
        )

        # ================= GENERATE BUTTON =================

        self.btn_generate = tk.Button(
            root,
            text="Generate PDF",
            command=self.process_data,
            bg="#1a1a1a",
            fg="white",
            font=('Arial', 10, 'bold'),
            padx=20,
            pady=10
        )

    # =========================================================
    # CONNECT SERVER
    # =========================================================

    def connect_server(self):

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

            self.conn = pyodbc.connect(
                conn_str,
                autocommit=True
            )

            self.cursor = self.conn.cursor()

            messagebox.showinfo(
                "Success",
                f"Connected Successfully to {unit}"
            )

            self.btn_generate.pack(pady=20)

        except Exception as e:

            messagebox.showerror(
                "Connection Error",
                str(e)
            )

    # =========================================================
    # OPTION CHANGE
    # =========================================================

    def option_changed(self, event=None):

        self.dept_dropdown.pack_forget()
        self.machine_entry.pack_forget()

        selected = self.option_dropdown.get()

        # ================= PARTICULAR DEPARTMENT =================

        if selected == "Particular Department":

            try:

                self.cursor.execute("""
                    SELECT DISTINCT DEPT
                    FROM OMCH
                    WHERE Active = 'Y'
                    ORDER BY DEPT ASC
                """)

                depts = [
                    str(row[0]).strip()
                    for row in self.cursor.fetchall()
                ]

                self.dept_dropdown['values'] = depts

                self.dept_dropdown.pack(pady=5)

            except Exception as e:

                messagebox.showerror(
                    "Error",
                    str(e)
                )

        # ================= PARTICULAR MACHINE =================

        elif selected == "Any Particular Machine":

            self.machine_entry.delete(0, tk.END)

            self.machine_entry.pack(pady=5)

    # =========================================================
    # CREATE QR
    # =========================================================

    def create_custom_qr(self, scan_data, center_text):

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )

        qr.add_data(scan_data)

        qr.make(fit=True)

        img = qr.make_image(
            fill_color="black",
            back_color="white"
        ).convert('RGB')

        draw = ImageDraw.Draw(img)

        width, height = img.size

        # ================= CENTER BOX =================

        box_width = 110
        box_height = 45

        pos_x = (width - box_width) // 2
        pos_y = (height - box_height) // 2

        draw.rectangle(
            [pos_x, pos_y, pos_x + box_width, pos_y + box_height],
            fill="white",
            outline="black"
        )

        try:

            font = ImageFont.truetype(
                "arial.ttf",
                16
            )

        except:

            font = ImageFont.load_default()

        text_bbox = draw.textbbox(
            (0, 0),
            center_text,
            font=font
        )

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

    # =========================================================
    # PROCESS DATA
    # =========================================================

    def process_data(self):

        try:

            selected_option = self.option_dropdown.get()

            query = ""

            # ================= ALL =================

            if selected_option == "All At A Glance":

                query = """
                    SELECT CODE,DEPT,CLD_McDesc
                    FROM OMCH
                    WHERE Active ='Y'
                """

            # ================= MILL SIDE =================

            elif selected_option == "Only Mill Side":

                query = """
                    SELECT CODE,DEPT,CLD_McDesc
                    FROM OMCH
                    WHERE Active ='Y'
                    AND DEPT IN('02','03','04','05','06')
                """

            # ================= FACTORY SIDE =================

            elif selected_option == "Only Factory Side":

                query = """
                    SELECT CODE,DEPT,CLD_McDesc
                    FROM OMCH
                    WHERE Active ='Y'
                    AND DEPT NOT IN('02','03','04','05','06')
                """

            # ================= PARTICULAR DEPT =================

            elif selected_option == "Particular Department":

                dept = self.dept_dropdown.get()

                if dept == "":

                    messagebox.showwarning(
                        "Warning",
                        "Please Select Department"
                    )

                    return

                query = f"""
                    SELECT CODE,DEPT,CLD_McDesc
                    FROM OMCH
                    WHERE Active ='Y'
                    AND DEPT = '{dept}'
                """

            # ================= PARTICULAR MACHINE =================

            elif selected_option == "Any Particular Machine":

                machine_no = self.machine_entry.get().strip()

                if len(machine_no) != 8:

                    messagebox.showwarning(
                        "Validation Error",
                        "Machine Number Must Be Exactly 8 Characters"
                    )

                    return

                query = f"""
                    SELECT CODE,DEPT,CLD_McDesc
                    FROM OMCH
                    WHERE Active ='Y'
                    AND CODE = '{machine_no}'
                """

            else:

                messagebox.showwarning(
                    "Warning",
                    "Please Select Any Option"
                )

                return

            # ================= EXECUTE QUERY =================

            self.cursor.execute(query)

            rows = self.cursor.fetchall()

            if rows:

                unit = self.unit_dropdown.get()

                self.generate_pdf(rows, unit)

            else:

                messagebox.showwarning(
                    "No Data",
                    "No Record Found"
                )

        except Exception as e:

            messagebox.showerror(
                "Error",
                str(e)
            )

    # =========================================================
    # PDF GENERATION
    # =========================================================

    def generate_pdf(self, data_rows, unit_name):

        # ================= SAVE LOCATION =================

        pdf_file = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=f"QR_Labels_{unit_name}.pdf",
            filetypes=[("PDF Files", "*.pdf")],
            title="Save PDF As"
        )

        # If user cancels save dialog
        if not pdf_file:
            return

        # ================= CREATE PDF =================

        c = canvas.Canvas(
            pdf_file,
            pagesize=A4
        )

        width, height = A4

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

            # ================= INDIAN TIME =================

            india_tz = pytz.timezone('Asia/Kolkata')

            generated_time = datetime.now(
                india_tz
            ).strftime(
                "%d-%m-%Y %I:%M:%S %p"
            )

            # ================= QR CONTENT =================

            scan_content = (
                f"MACHINE NO: {code}\n"
                f"DEPT: {dept}\n"
                f"LOCATION: {unit_name}\n"
                f"MC DESC : {CLD_McDesc}\n"
                f"GENERATED DATE & TIME : {generated_time}"
            )

            # ================= CREATE QR =================

            qr_img = self.create_custom_qr(
                scan_content,
                code
            )

            temp_path = f"temp_{i}.png"

            qr_img.save(temp_path)

            # ================= GRID POSITION =================

            page_pos = i % 12

            col = page_pos % cols
            row = page_pos // cols

            x = x_margin + col * (
                qr_size + x_space
            )

            y = (
                height
                - y_margin
                - (row + 1) * qr_size
                - (row * y_space)
            )

            # ================= DRAW IMAGE =================

            c.drawImage(
                temp_path,
                x,
                y,
                width=qr_size,
                height=qr_size
            )

            os.remove(temp_path)

            # ================= NEW PAGE =================

            if (
                (i + 1) % 12 == 0
                and
                (i + 1) < len(data_rows)
            ):

                c.showPage()

        c.save()

        messagebox.showinfo(
            "Success",
            f"PDF Saved Successfully\n\nLocation:\n{pdf_file}"
        )


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    app = QRCodeGeneratorApp(root)

    root.mainloop()
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

        # ================= DEPARTMENT MAP =================

        self.dept_map = {
            '01': 'JUTE',
            '02': 'BATCHING',
            '03': 'CARDING',
            '04': 'DRAWING',
            '05': 'SPINNING',
            '06': 'WINDING',
            '07': 'WEAVING SACKING',
            '08': 'MILL MECHANIC',
            '09': 'BEAMING',
            '10': 'WEAVING HESSIAN',
            '11': 'FINISHING',
            '12': 'SEWING',
            '13': 'DORNIER WEAVING',
            '14': 'BALING/PRESS',
            '15': 'FACTORY MECHANIC',
            '16': 'SHIPPING',
            '17': 'WEAVING MODERN/RAPIER',
            '18': 'WEAVING S4A',
            '19': 'WORK SHOP',
            '20': 'POWER HOUSE & GEN. HOUSE',
            '21': 'PUMP HOUSE',
            '22': 'BOILER HOUSE',
            '24': 'S.Q.C.',
            '25': 'GENERAL OUTSIDE'
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

        server   = r'202.140.137.225\STILDB,8181'
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

            self.conn   = pyodbc.connect(conn_str, autocommit=True)
            self.cursor = self.conn.cursor()

            messagebox.showinfo(
                "Success",
                f"Connected Successfully to {unit}"
            )

            self.btn_generate.pack(pady=20)

        except Exception as e:

            messagebox.showerror("Connection Error", str(e))

    # =========================================================
    # OPTION CHANGE
    # =========================================================

    def option_changed(self, event=None):

        self.dept_dropdown.pack_forget()
        self.machine_entry.pack_forget()

        selected = self.option_dropdown.get()

        if selected == "Particular Department":

            try:

                self.cursor.execute("""
                    SELECT DISTINCT DEPT
                    FROM OMCH
                    WHERE Active = 'Y'
                    ORDER BY DEPT ASC
                """)

                dept_rows        = self.cursor.fetchall()
                dept_display_list = []

                for row in dept_rows:

                    dept_code = str(row[0]).strip()
                    dept_name = self.dept_map.get(dept_code, "UNKNOWN")
                    dept_display_list.append(f"{dept_code} ({dept_name})")

                self.dept_dropdown['values'] = dept_display_list
                self.dept_dropdown.pack(pady=5)

            except Exception as e:

                messagebox.showerror("Error", str(e))

        elif selected == "Any Particular Machine":

            self.machine_entry.delete(0, tk.END)
            self.machine_entry.pack(pady=5)

    # =========================================================
    # CREATE QR  ── ORIGINAL (UNCHANGED)
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

        draw          = ImageDraw.Draw(img)
        width, height = img.size

        box_width  = 110
        box_height = 45
        pos_x      = (width  - box_width)  // 2
        pos_y      = (height - box_height) // 2

        draw.rectangle(
            [pos_x, pos_y, pos_x + box_width, pos_y + box_height],
            fill="white",
            outline="black"
        )

        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except:
            font = ImageFont.load_default()

        text_bbox = draw.textbbox((0, 0), center_text, font=font)
        text_w    = text_bbox[2] - text_bbox[0]
        text_h    = text_bbox[3] - text_bbox[1]

        draw.text(
            (
                pos_x + (box_width  - text_w) / 2,
                pos_y + (box_height - text_h) / 2 - 2
            ),
            center_text,
            fill="black",
            font=font
        )

        return img

    # =========================================================
    # CREATE WHATSAPP QR
    # ---------------------------------------------------------
    # Encodes only the whatsapp:// deep-link URI.
    # This native-app scheme is recognised by BOTH iPhone and
    # Android cameras as "open in app" — not a web URL — so
    # neither OS auto-redirects; they ask the user first or
    # open WhatsApp directly depending on the scanner app.
    # The center badge shows the WhatsApp icon text clearly.
    # =========================================================

    def create_whatsapp_qr(self, center_text):

        # Native deep-link — works on iPhone & Android
        wa_data = "https://wa.me/919775330074?text=Hi"

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )

        qr.add_data(wa_data)
        qr.make(fit=True)

        # Green modules for visual distinction
        img = qr.make_image(
            fill_color="#128C7E",   # WhatsApp dark green
            back_color="white"
        ).convert('RGB')

        draw          = ImageDraw.Draw(img)
        width, height = img.size

        # ── Centre badge ──────────────────────────────────────

        box_width  = 120
        box_height = 45
        pos_x      = (width  - box_width)  // 2
        pos_y      = (height - box_height) // 2

        draw.rectangle(
            [pos_x, pos_y, pos_x + box_width, pos_y + box_height],
            fill="#25D366",        # WhatsApp light green
            outline="#128C7E"
        )

        try:
            font = ImageFont.truetype("arial.ttf", 13)
        except:
            font = ImageFont.load_default()

        badge_text = "WhatsApp"
        text_bbox  = draw.textbbox((0, 0), badge_text, font=font)
        text_w     = text_bbox[2] - text_bbox[0]
        text_h     = text_bbox[3] - text_bbox[1]

        draw.text(
            (
                pos_x + (box_width  - text_w) / 2,
                pos_y + (box_height - text_h) / 2 - 2
            ),
            badge_text,
            fill="white",
            font=font
        )

        return img

    # =========================================================
    # PROCESS DATA
    # =========================================================

    def process_data(self):

        try:

            selected_option = self.option_dropdown.get()
            query           = ""

            if selected_option == "All At A Glance":

                query = """
                    SELECT CODE,DEPT,CLD_McDesc
                    FROM OMCH WHERE Active ='Y'
                """

            elif selected_option == "Only Mill Side":

                query = """
                    SELECT CODE,DEPT,CLD_McDesc
                    FROM OMCH WHERE Active ='Y'
                    AND DEPT IN('02','03','04','05','06')
                """

            elif selected_option == "Only Factory Side":

                query = """
                    SELECT CODE,DEPT,CLD_McDesc
                    FROM OMCH WHERE Active ='Y'
                    AND DEPT NOT IN('02','03','04','05','06')
                """

            elif selected_option == "Particular Department":

                dept_value = self.dept_dropdown.get()

                if dept_value == "":
                    messagebox.showwarning("Warning", "Please Select Department")
                    return

                dept  = dept_value.split(" ")[0]
                query = f"""
                    SELECT CODE,DEPT,CLD_McDesc
                    FROM OMCH WHERE Active ='Y'
                    AND DEPT = '{dept}'
                """

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
                    FROM OMCH WHERE Active ='Y'
                    AND CODE = '{machine_no}'
                """

            else:
                messagebox.showwarning("Warning", "Please Select Any Option")
                return

            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            if rows:
                unit = self.unit_dropdown.get()
                self.generate_pdf(rows, unit)
            else:
                messagebox.showwarning("No Data", "No Record Found")

        except Exception as e:
            messagebox.showerror("Error", str(e))

    # =========================================================
    # PDF GENERATION
    # ---------------------------------------------------------
    # Layout: 2 machines per row, each machine gets a PAIR of
    # QR codes side by side inside a labelled box:
    #
    #   [ MACHINE DETAILS QR ]  [ WHATSAPP QR ]
    #        "Scan for Info"     "Scan for WhatsApp"
    #
    # 2 machines per row × 3 rows = 6 machines per page.
    # =========================================================

    def generate_pdf(self, data_rows, unit_name):

        pdf_file = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            initialfile=f"QR_Labels_{unit_name}.pdf",
            filetypes=[("PDF Files", "*.pdf")],
            title="Save PDF As"
        )

        if not pdf_file:
            return

        c             = canvas.Canvas(pdf_file, pagesize=A4)
        page_w, page_h = A4

        # ── Grid settings ─────────────────────────────────────

        machines_per_row  = 2          # machines across the page
        rows_per_page     = 3          # machine rows per page
        machines_per_page = machines_per_row * rows_per_page   # 6

        x_margin  = 30
        y_margin  = 40

        # Each machine block holds 2 QRs side by side
        qr_size   = 110                # individual QR image size
        gap_inner = 6                  # gap between the two QRs
        pad       = 8                  # padding inside machine block
        label_h   = 14                 # height reserved for label text

        block_w   = pad + qr_size + gap_inner + qr_size + pad
        block_h   = pad + qr_size + label_h   + pad

        # Space between machine blocks
        h_space   = (
            (page_w - 2 * x_margin - machines_per_row * block_w)
            / (machines_per_row - 1)
        )

        v_space   = (
            (page_h - 2 * y_margin - rows_per_page * block_h)
            / (rows_per_page - 1)
        )

        try:
            from reportlab.lib.units import mm
            from reportlab.pdfbase import pdfmetrics
            label_font_size = 7
        except:
            label_font_size = 7

        for i, record in enumerate(data_rows):

            code         = str(record[0]).strip()
            dept         = str(record[1]).strip()
            dept_name    = self.dept_map.get(dept, "UNKNOWN")
            dept_display = f"{dept} ({dept_name})"
            CLD_McDesc   = str(record[2]).strip()

            # ── Indian time ───────────────────────────────────

            india_tz       = pytz.timezone('Asia/Kolkata')
            generated_time = datetime.now(india_tz).strftime(
                "%d-%m-%Y %I:%M:%S %p"
            )

            # ── Scan content for DETAILS QR ───────────────────
            # Plain text only — no URL — so every scanner on
            # every device shows text, never auto-redirects.

            details_content = (
                f"================================\n"
                f"        MACHINE  DETAILS\n"
                f"================================\n"
                f"\n"
                f" MACHINE NO  : {code}\n"
                f" DEPARTMENT  : {dept_display}\n"
                f" LOCATION    : {unit_name}\n"
                f" DESCRIPTION : {CLD_McDesc}\n"
                f"\n"
                f" GENERATED   : {generated_time}\n"
                f"================================"
            )

            # ── Generate both QR images ───────────────────────

            details_img  = self.create_custom_qr(details_content, code)
            whatsapp_img = self.create_whatsapp_qr(code)

            temp_details  = f"tmp_det_{i}.png"
            temp_whatsapp = f"tmp_wa_{i}.png"

            details_img.save(temp_details)
            whatsapp_img.save(temp_whatsapp)

            # ── Grid position ─────────────────────────────────

            page_pos  = i % machines_per_page
            col       = page_pos % machines_per_row
            row       = page_pos // machines_per_row

            block_x   = x_margin + col * (block_w + h_space)
            block_y   = (
                page_h
                - y_margin
                - (row + 1) * block_h
                - row * v_space
            )

            # ── Draw outer box for machine block ──────────────

            c.setStrokeColorRGB(0.7, 0.7, 0.7)
            c.setLineWidth(0.5)
            c.rect(block_x, block_y, block_w, block_h)

            # ── Draw details QR (left) ────────────────────────

            det_x = block_x + pad
            det_y = block_y + pad + label_h

            c.drawImage(
                temp_details,
                det_x, det_y,
                width=qr_size, height=qr_size
            )

            # ── Draw WhatsApp QR (right) ──────────────────────

            wa_x = det_x + qr_size + gap_inner
            wa_y = det_y

            c.drawImage(
                temp_whatsapp,
                wa_x, wa_y,
                width=qr_size, height=qr_size
            )

            # ── Labels below each QR ──────────────────────────

            c.setFont("Helvetica-Bold", label_font_size)

            # Machine code centred under details QR
            c.setFillColorRGB(0, 0, 0)
            det_label = f"{code}  |  Scan for Details"
            c.drawCentredString(
                det_x + qr_size / 2,
                block_y + pad + 3,
                det_label
            )

            # WhatsApp label in green
            c.setFillColorRGB(0.07, 0.55, 0.43)   # #128C7E
            wa_label = "Scan for WhatsApp"
            c.drawCentredString(
                wa_x + qr_size / 2,
                block_y + pad + 3,
                wa_label
            )

            c.setFillColorRGB(0, 0, 0)

            # ── Divider line between the two QRs ─────────────

            mid_x = det_x + qr_size + gap_inner / 2
            c.setStrokeColorRGB(0.85, 0.85, 0.85)
            c.setLineWidth(0.4)
            c.line(mid_x, block_y + 4, mid_x, block_y + block_h - 4)

            # ── Clean up temp files ───────────────────────────

            os.remove(temp_details)
            os.remove(temp_whatsapp)

            # ── New page every 6 machines ─────────────────────

            if (
                (i + 1) % machines_per_page == 0
                and (i + 1) < len(data_rows)
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
    app  = QRCodeGeneratorApp(root)
    root.mainloop()
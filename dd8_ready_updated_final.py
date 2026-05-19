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


# =========================================================
# THEME
# =========================================================

BG_MAIN      = "#0d0d14"
BG_CARD      = "#13131f"
BG_INPUT     = "#1c1c2e"
ACCENT_CYAN  = "#00e5ff"
ACCENT_GREEN = "#00ff9d"
ACCENT_RED   = "#ff4466"
TEXT_WHITE   = "#eeeef5"
TEXT_DIM     = "#55556a"
BORDER       = "#25253a"


# =========================================================
# HOVER BUTTON
# =========================================================

class HoverButton(tk.Button):

    def __init__(self, master,
                 n_bg, n_fg,
                 h_bg, h_fg,
                 **kwargs):

        super().__init__(
            master,
            bg=n_bg, fg=n_fg,
            activebackground=h_bg,
            activeforeground=h_fg,
            relief="flat", bd=0,
            cursor="hand2",
            **kwargs
        )

        self._n_bg = n_bg
        self._n_fg = n_fg
        self._h_bg = h_bg
        self._h_fg = h_fg

        self.bind("<Enter>", lambda e: self.config(bg=self._h_bg, fg=self._h_fg))
        self.bind("<Leave>", lambda e: self.config(bg=self._n_bg, fg=self._n_fg))


# =========================================================
# APP
# =========================================================

class QRCodeGeneratorApp:

    def __init__(self, root):

        self.root = root
        self.root.title("Industrial QR Generator")
        self.root.geometry("480x620")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_MAIN)

        self._apply_styles()

        # ================= DATABASE MAP =================

        self.db_map = {
            'SHJM': 'Smart_Eye_Jute_STIL_Hastings_Live',
            'MIJM': 'Smart_Eye_Jute_STIL_India_Live',
            'SGJM': 'Smart_Eye_Jute_STIL_Gondalpara_Live',
            'SSKT': 'Smart_Eye_Jute_STIL_Shaktigarh_Live'
        }

        # ================= DEPARTMENT MAP =================

        self.dept_map = {
            '01': 'JUTE',              '02': 'BATCHING',
            '03': 'CARDING',           '04': 'DRAWING',
            '05': 'SPINNING',          '06': 'WINDING',
            '07': 'WEAVING SACKING',   '08': 'MILL MECHANIC',
            '09': 'BEAMING',           '10': 'WEAVING HESSIAN',
            '11': 'FINISHING',         '12': 'SEWING',
            '13': 'DORNIER WEAVING',   '14': 'BALING/PRESS',
            '15': 'FACTORY MECHANIC',  '16': 'SHIPPING',
            '17': 'WEAVING MODERN/RAPIER', '18': 'WEAVING S4A',
            '19': 'WORK SHOP',         '20': 'POWER HOUSE & GEN. HOUSE',
            '21': 'PUMP HOUSE',        '22': 'BOILER HOUSE',
            '24': 'S.Q.C.',            '25': 'GENERAL OUTSIDE'
        }

        self.conn   = None
        self.cursor = None

        self._build_ui()

    # =========================================================
    # STYLES
    # =========================================================

    def _apply_styles(self):

        s = ttk.Style()
        s.theme_use("clam")

        s.configure("D.TCombobox",
            fieldbackground=BG_INPUT,
            background=BG_INPUT,
            foreground=TEXT_WHITE,
            bordercolor=BORDER,
            arrowcolor=ACCENT_CYAN,
            selectbackground=BG_INPUT,
            selectforeground=ACCENT_CYAN,
            relief="flat",
            padding=(10, 8)
        )

        s.map("D.TCombobox",
            fieldbackground=[("readonly", BG_INPUT)],
            foreground=[("readonly", TEXT_WHITE)],
            bordercolor=[("focus", ACCENT_CYAN)]
        )

    # =========================================================
    # BUILD UI
    # =========================================================

    def _build_ui(self):

        # ── TOP ACCENT LINE ──
        tk.Frame(self.root, bg=ACCENT_CYAN, height=2).pack(fill="x")

        # ── HEADER ──
        hdr = tk.Frame(self.root, bg=BG_CARD)
        hdr.pack(fill="x")

        tk.Label(
            hdr,
            text="INDUSTRIAL QR GENERATOR",
            font=("Courier New", 13, "bold"),
            bg=BG_CARD, fg=ACCENT_CYAN,
            pady=14
        ).pack()

        tk.Label(
            hdr,
            text="MACHINE LABEL PRODUCTION SYSTEM  •  STIL GROUP",
            font=("Courier New", 7),
            bg=BG_CARD, fg=TEXT_DIM
        ).pack()

        tk.Frame(hdr, bg=BORDER, height=1).pack(fill="x", pady=(12, 0))

        # ── BODY ──
        body = tk.Frame(self.root, bg=BG_MAIN)
        body.pack(fill="both", expand=True, padx=40, pady=20)

        # ─── SECTION 1: Manufacturing Unit ───
        self._section_label(body, "MANUFACTURING UNIT")

        self.unit_dropdown = ttk.Combobox(
            body,
            values=list(self.db_map.keys()),
            state="readonly",
            width=44,
            style="D.TCombobox"
        )
        self.unit_dropdown.pack(fill="x", pady=(0, 14))
        self.unit_dropdown.set("SHJM")

        # ─── CONNECT BUTTON ───
        self.connect_btn = HoverButton(
            body,
            n_bg="#0a2a1a", n_fg=ACCENT_GREEN,
            h_bg=ACCENT_GREEN, h_fg="#000000",
            text="◈   CONNECT TO SERVER",
            font=("Courier New", 9, "bold"),
            pady=10,
            command=self.connect_server,
            highlightthickness=1,
            highlightbackground=ACCENT_GREEN,
            highlightcolor=ACCENT_GREEN
        )
        self.connect_btn.pack(fill="x", pady=(0, 18))

        # ─── DIVIDER ───
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(0, 16))

        # ─── SECTION 2: QR Generation Type ───
        self._section_label(body, "QR GENERATION TYPE")

        self.option_dropdown = ttk.Combobox(
            body,
            state="readonly",
            width=44,
            style="D.TCombobox",
            values=[
                "All At A Glance",
                "Only Mill Side",
                "Only Factory Side",
                "Particular Department",
                "Any Particular Machine"
            ]
        )
        self.option_dropdown.pack(fill="x", pady=(0, 10))
        self.option_dropdown.bind("<<ComboboxSelected>>", self.option_changed)

        # ─── DYNAMIC FRAME (dept/machine — always packed here, above buttons) ───
        self.dynamic_frame = tk.Frame(body, bg=BG_MAIN)
        self.dynamic_frame.pack(fill="x")

        self.dept_dropdown = ttk.Combobox(
            self.dynamic_frame,
            state="readonly",
            width=44,
            style="D.TCombobox"
        )

        self.machine_entry = tk.Entry(
            self.dynamic_frame,
            font=("Courier New", 10),
            bg=BG_INPUT, fg=ACCENT_CYAN,
            insertbackground=ACCENT_CYAN,
            relief="flat", bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT_CYAN
        )

        # ─── DIVIDER ───
        tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=(14, 14))

        # ─── STATUS TEXT (above buttons) ───
        self.status_var = tk.StringVar(value="●  SYSTEM READY")

        tk.Label(
            body,
            textvariable=self.status_var,
            font=("Courier New", 7),
            bg=BG_MAIN, fg=TEXT_DIM,
            anchor="w"
        ).pack(fill="x", pady=(0, 10))

        # ─── GENERATE BUTTON (hidden until connected) ───
        self.btn_generate = HoverButton(
            body,
            n_bg="#001a22", n_fg=ACCENT_CYAN,
            h_bg=ACCENT_CYAN, h_fg="#000000",
            text="▣   GENERATE PDF",
            font=("Courier New", 9, "bold"),
            pady=10,
            command=self.process_data,
            highlightthickness=1,
            highlightbackground=ACCENT_CYAN,
            highlightcolor=ACCENT_CYAN
        )

        # ─── EXIT BUTTON ───
        self.btn_exit = HoverButton(
            body,
            n_bg="#22000e", n_fg=ACCENT_RED,
            h_bg=ACCENT_RED, h_fg="#ffffff",
            text="✕   EXIT APPLICATION",
            font=("Courier New", 9, "bold"),
            pady=10,
            command=self._confirm_exit,
            highlightthickness=1,
            highlightbackground=ACCENT_RED,
            highlightcolor=ACCENT_RED
        )
        self.btn_exit.pack(fill="x")

    # ─── section label helper ───
    def _section_label(self, parent, text):

        tk.Label(
            parent,
            text=text,
            font=("Courier New", 7, "bold"),
            bg=BG_MAIN, fg=ACCENT_CYAN,
            anchor="w"
        ).pack(fill="x", pady=(0, 5))

    # =========================================================
    # EXIT
    # =========================================================

    def _confirm_exit(self):

        if messagebox.askyesno("Exit", "Are you sure you want to exit?"):
            self.root.destroy()

    # =========================================================
    # CONNECT SERVER
    # =========================================================

    def connect_server(self):

        unit    = self.unit_dropdown.get()
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

            messagebox.showinfo("Success", f"Connected Successfully to {unit}")

            self.status_var.set(f"●  CONNECTED  →  {unit}")

            # Show Generate PDF above Exit
            self.btn_generate.pack(fill="x", pady=(0, 8), before=self.btn_exit)

        except Exception as e:

            messagebox.showerror("Connection Error", str(e))
            self.status_var.set("●  CONNECTION FAILED")

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
                    SELECT DISTINCT DEPT FROM OMCH WHERE Active = 'Y'
                    UNION
                    SELECT DISTINCT DEPT FROM OMCH
                    WHERE Active = 'N' AND DEPT = '06'
                    AND CLD_McNo <> '0' AND LEN(CLD_McNo) <> 1
                    ORDER BY DEPT ASC
                """)

                dept_rows         = self.cursor.fetchall()
                dept_display_list = []

                for row in dept_rows:
                    dept_code = str(row[0]).strip()
                    dept_name = self.dept_map.get(dept_code, "UNKNOWN")
                    dept_display_list.append(f"{dept_code} ({dept_name})")

                self.dept_dropdown['values'] = dept_display_list
                self.dept_dropdown.pack(fill="x", pady=(0, 10))

            except Exception as e:
                messagebox.showerror("Error", str(e))

        # ================= PARTICULAR MACHINE =================

        elif selected == "Any Particular Machine":

            self.machine_entry.delete(0, tk.END)
            self.machine_entry.pack(fill="x", pady=(0, 10), ipady=8)

    # =========================================================
    # CREATE QR  ── 100% ORIGINAL, ZERO CHANGES
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
            fill="white", outline="black"
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
            center_text, fill="black", font=font
        )

        return img

    # =========================================================
    # PROCESS DATA
    # =========================================================

    def process_data(self):

        try:

            selected_option = self.option_dropdown.get()
            query           = ""

            # ── ALL AT A GLANCE ──
            if selected_option == "All At A Glance":

                query = """
                    SELECT CODE, DEPT, CLD_McNo, CLD_McDesc
                    FROM OMCH WHERE Active = 'Y' AND DEPT <> '06'
                    UNION ALL
                    SELECT CODE, DEPT, CLD_McNo, CLD_McDesc
                    FROM OMCH WHERE Active = 'N' AND DEPT = '06'
                    AND CLD_McNo <> '0' AND LEN(CLD_McNo) <> 1
                """

            # ── ONLY MILL SIDE ──
            elif selected_option == "Only Mill Side":

                query = """
                    SELECT CODE, DEPT, CLD_McNo, CLD_McDesc
                    FROM OMCH WHERE Active = 'Y'
                    AND DEPT IN ('02','03','04','05')
                    UNION ALL
                    SELECT CODE, DEPT, CLD_McNo, CLD_McDesc
                    FROM OMCH WHERE Active = 'N' AND DEPT = '06'
                    AND CLD_McNo <> '0' AND LEN(CLD_McNo) <> 1
                """

            # ── ONLY FACTORY SIDE ──
            elif selected_option == "Only Factory Side":

                query = """
                    SELECT CODE, DEPT, CLD_McNo, CLD_McDesc
                    FROM OMCH WHERE Active = 'Y'
                    AND DEPT NOT IN ('02','03','04','05','06')
                """

            # ── PARTICULAR DEPARTMENT ──
            elif selected_option == "Particular Department":

                dept_value = self.dept_dropdown.get()

                if dept_value == "":
                    messagebox.showwarning("Warning", "Please Select Department")
                    return

                dept = dept_value.split(" ")[0]

                if dept == '06':
                    query = """
                        SELECT CODE, DEPT, CLD_McNo, CLD_McDesc
                        FROM OMCH WHERE Active = 'N' AND DEPT = '06'
                        AND CLD_McNo <> '0' AND LEN(CLD_McNo) <> 1
                    """
                else:
                    query = f"""
                        SELECT CODE, DEPT, CLD_McNo, CLD_McDesc
                        FROM OMCH WHERE Active = 'Y' AND DEPT = '{dept}'
                    """

            # ── ANY PARTICULAR MACHINE ──
            elif selected_option == "Any Particular Machine":

                machine_no = self.machine_entry.get().strip()

                if len(machine_no) != 8:
                    messagebox.showwarning(
                        "Validation Error",
                        "Machine Number Must Be Exactly 8 Characters"
                    )
                    return

                query = f"""
                    SELECT CODE, DEPT, CLD_McNo, CLD_McDesc
                    FROM OMCH
                    WHERE CODE = '{machine_no}'
                    AND (
                        Active = 'Y'
                        OR (
                            Active = 'N' AND DEPT = '06'
                            AND CLD_McNo <> '0'
                            AND LEN(CLD_McNo) <> 1
                        )
                    )
                """

            else:
                messagebox.showwarning("Warning", "Please Select Any Option")
                return

            # ── EXECUTE ──
            self.cursor.execute(query)
            rows = self.cursor.fetchall()

            if rows:
                unit = self.unit_dropdown.get()
                self.status_var.set(f"●  GENERATING  →  {len(rows)} RECORDS")
                self.generate_pdf(rows, unit)
            else:
                messagebox.showwarning("No Data", "No Record Found")
                self.status_var.set("●  NO RECORDS FOUND")

        except Exception as e:
            messagebox.showerror("Error", str(e))
            self.status_var.set("●  ERROR OCCURRED")

    # =========================================================
    # PDF GENERATION
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
        width, height = A4

        cols          = 3
        rows_per_page = 4
        x_margin      = 50
        y_margin      = 72          # increased from 60 to give space for label
        qr_size       = 145

        x_space = (width  - 2*x_margin - cols*qr_size) / (cols - 1)
        y_space = (height - 2*y_margin - rows_per_page*qr_size) / (rows_per_page - 1)

        for i, record in enumerate(data_rows):

            code         = str(record[0]).strip()
            dept         = str(record[1]).strip()
            dept_name    = self.dept_map.get(dept, "UNKNOWN")
            dept_display = f"{dept} ({dept_name})"
            CLD_McNo     = str(record[2]).strip()
            CLD_McDesc   = str(record[3]).strip()

            india_tz       = pytz.timezone('Asia/Kolkata')
            generated_time = datetime.now(india_tz).strftime(
                "%d-%m-%Y %I:%M:%S %p"
            )

            scan_content = (
                f"================================\n"
                f"        MACHINE  DETAILS\n"
                f"================================\n"
                f"\n"
                f" MACHINE NO   : {code}\n"
                f" EQUIPMENT NO : {CLD_McNo}\n"
                f" DEPARTMENT   : {dept_display}\n"
                f" LOCATION     : {unit_name}\n"
                f" DESCRIPTION  : {CLD_McDesc}\n"
                f"\n"
                f" GENERATED    : {generated_time}\n"
                f"\n"
                f"--------------------------------\n"
                f"   SEND A MESSAGE ON WHATSAPP\n"
                f"--------------------------------\n"
                f"\n"
                f"https://wa.me/918100149341?text={code}"
            )

            qr_img    = self.create_custom_qr(scan_content, code)
            temp_path = f"temp_{i}.png"
            qr_img.save(temp_path)

            page_pos = i % 12
            col      = page_pos % cols
            row      = page_pos // cols

            x = x_margin + col * (qr_size + x_space)
            y = height - y_margin - (row + 1) * qr_size - row * y_space

            # ── DRAW QR IMAGE ──
            c.drawImage(temp_path, x, y, width=qr_size, height=qr_size)
            os.remove(temp_path)

            # ── MACHINE CODE LABEL BELOW QR ──
            c.setFont("Courier-Bold", 8)
            c.setFillColorRGB(0, 0, 0)
            c.drawCentredString(x + qr_size / 2, y - 12, code)

            if (i + 1) % 12 == 0 and (i + 1) < len(data_rows):
                c.showPage()

        c.save()

        self.status_var.set(f"●  PDF SAVED  →  {len(data_rows)} LABELS")

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
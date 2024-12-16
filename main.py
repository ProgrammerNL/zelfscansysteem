import cv2
from pyzbar.pyzbar import decode
import tkinter as tk
from tkinter import messagebox
from flask import Flask, jsonify, render_template
import threading

actieve_scanners = {}

app = Flask(__name__)

@app.route("/")
def overzicht():
    """Manager-overzichtspagina."""
    return render_template("index.html", scanners=actieve_scanners)

@app.route("/api/scanners", methods=["GET"])
def api_scanners():
    """API voor actieve scanners."""
    return jsonify(actieve_scanners)

class ZelfScanKassa:
    def __init__(self, scanner_id):
        self.scanner_id = scanner_id
        self.producten = {
            "123456": {"naam": "Appel", "prijs": 0.5},
            "789101": {"naam": "Banaan", "prijs": 0.3},
            "112233": {"naam": "Melk", "prijs": 1.2},
            "445566": {"naam": "Brood", "prijs": 1.5},
        }
        self.winkelwagen = {}

    def voeg_toe_aan_winkelwagen(self, code):
        if code in self.producten:
            if code in self.winkelwagen:
                self.winkelwagen[code] += 1
            else:
                self.winkelwagen[code] = 1
            self.update_scanner_status()
            return f"{self.producten[code]['naam']} toegevoegd aan de winkelwagen."
        else:
            return "Ongeldige barcode of product niet gevonden."

    def toon_winkelwagen(self):
        items = []
        totaal = 0
        for code, aantal in self.winkelwagen.items():
            naam = self.producten[code]['naam']
            prijs = self.producten[code]['prijs'] * aantal
            totaal += prijs
            items.append(f"{aantal}x {naam} - €{prijs:.2f}")
        items.append(f"Totaal: €{totaal:.2f}")
        return "\n".join(items), totaal

    def update_scanner_status(self):
        """Update de status van deze scanner op de server."""
        actieve_scanners[self.scanner_id] = {
            "winkelwagen": self.winkelwagen,
        }

    def afrekenen(self, betaald_bedrag):
        totaal = sum(self.producten[code]['prijs'] * aantal for code, aantal in self.winkelwagen.items())
        if betaald_bedrag >= totaal:
            wisselgeld = betaald_bedrag - totaal
            self.winkelwagen.clear()
            self.update_scanner_status()
            return f"Betaling gelukt! Wisselgeld: €{wisselgeld:.2f}"
        else:
            return "Onvoldoende betaling."

class ZelfScanApp:
    def __init__(self, root, scanner_id):
        self.scanner_id = scanner_id
        self.kassa = ZelfScanKassa(scanner_id)
        self.root = root
        self.root.title(f"Zelf-Scan Kassa - {scanner_id}")
        self.scanning = False

        
        self.label_cart = tk.Label(root, text="Winkelwagen:")
        self.label_cart.pack()
        self.text_cart = tk.Text(root, height=10, width=40, state=tk.DISABLED)
        self.text_cart.pack()

        
        self.btn_start_scan = tk.Button(root, text="Start Scannen", command=self.start_scanning)
        self.btn_start_scan.pack()

        self.label_payment = tk.Label(root, text="Betaal bedrag:")
        self.label_payment.pack()
        self.entry_payment = tk.Entry(root)
        self.entry_payment.pack()
        self.btn_checkout = tk.Button(root, text="Afrekenen", command=self.checkout)
        self.btn_checkout.pack()
        
        actieve_scanners[scanner_id] = {"winkelwagen": {}}

    def start_scanning(self):
        self.scanning = True
        self.capture_video()

    def capture_video(self):
        camera_url = "http://192.168.1.100:8080/video"  
        cap = cv2.VideoCapture(camera_url)

        if not cap.isOpened():
            messagebox.showerror("Fout", "Kan geen verbinding maken met de camera.")
            return

        while self.scanning:
            ret, frame = cap.read()
            if not ret:
                break

            barcodes = decode(frame)
            for barcode in barcodes:
                if barcode.type == "QRCODE":  
                    barcode_data = barcode.data.decode('utf-8')
                    message = self.kassa.voeg_toe_aan_winkelwagen(barcode_data)
                    self.update_cart()
                    messagebox.showinfo("Product Toegevoegd", message)

            cv2.imshow("Scan Producten", frame)

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self.scanning = False
                break

        cap.release()
        cv2.destroyAllWindows()

    def update_cart(self):
        items, _ = self.kassa.toon_winkelwagen()
        self.text_cart.config(state=tk.NORMAL)
        self.text_cart.delete(1.0, tk.END)
        self.text_cart.insert(tk.END, items)
        self.text_cart.config(state=tk.DISABLED)

    def checkout(self):
        try:
            betaald_bedrag = float(self.entry_payment.get())
            message = self.kassa.afrekenen(betaald_bedrag)
            self.entry_payment.delete(0, tk.END)
            self.update_cart()
            messagebox.showinfo("Afrekenen", message)
        except ValueError:
            messagebox.showerror("Fout", "Voer een geldig bedrag in.")

def start_gui(scanner_id):
    root = tk.Tk()
    app = ZelfScanApp(root, scanner_id)
    root.mainloop()

def start_server():
    app.run(port=5000, debug=True)

if __name__ == "__main__":
    
    threading.Thread(target=start_gui, args=("Scanner1",), daemon=True).start()
    start_server()  

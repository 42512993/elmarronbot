import sys
import concurrent.futures
import requests
from bs4 import BeautifulSoup
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QLabel
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

# Configuración de Telegram
TELEGRAM_BOT_TOKEN = "7755285253:AAGsOAl9t8JOPCrSpqU4cMCo5hQjm_tkgqY"
TELEGRAM_CHAT_ID = "1323687738"

class DataFetcher(QThread):
    data_fetched = pyqtSignal(list)
    alert_triggered = pyqtSignal(str)
    
    def __init__(self, pais, acciones):
        super().__init__()
        self.pais = pais
        self.acciones = acciones
    
    def run(self):
        data = []
        headers = {"User-Agent": "Mozilla/5.0"}
        
        def obtener_datos(accion):
            url = f"https://www.google.com/finance/quote/{accion}"
            response = requests.get(url, headers=headers)
            soup = BeautifulSoup(response.text, "html.parser")
            try:
                precio = soup.find("div", class_="YMlKec fxKbKc").text.replace('$', '')
                variacion = soup.find("div", class_="JwB6zf").text.replace('%', '')
                tendencia = "▲" if float(variacion) > 0 else "▼" if float(variacion) < 0 else "-"
                
                # Disparar alerta si la variación es mayor al 5%
                if abs(float(variacion)) > 3:
                    alerta_msg = f"⚠️ Alerta en {accion}: Variación {variacion}% ({'Sube' if float(variacion) > 0 else 'Baja'})"
                    self.alert_triggered.emit(alerta_msg)
                
                return (accion, precio, tendencia, variacion + "%")
            except:
                return (accion, "No disponible", "-", "-")
        
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(obtener_datos, self.acciones)
            data.extend(results)
        
        self.data_fetched.emit(data)

class StockApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mercado de Acciones")
        
        layout = QVBoxLayout()
        
        self.label = QLabel("Seleccione un país:")
        layout.addWidget(self.label)
        
        self.btn_eeuu = QPushButton("EEUU")
        self.btn_eeuu.clicked.connect(lambda: self.obtener_precios("EEUU"))
        layout.addWidget(self.btn_eeuu)
        
        self.btn_arg = QPushButton("Argentina")
        self.btn_arg.clicked.connect(lambda: self.obtener_precios("Argentina"))
        layout.addWidget(self.btn_arg)
        
        self.btn_bra = QPushButton("Brasil")
        self.btn_bra.clicked.connect(lambda: self.obtener_precios("Brasil"))
        layout.addWidget(self.btn_bra)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Acción", "Precio", "Tendencia", "Variación (%)"])
        layout.addWidget(self.table)
        
        self.pin_button = QPushButton("Mantener siempre arriba")
        self.pin_button.setCheckable(True)
        self.pin_button.clicked.connect(self.toggle_always_on_top)
        layout.addWidget(self.pin_button)
        
        self.chart_label = QLabel()
        layout.addWidget(self.chart_label)
        
        self.setLayout(layout)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar_precios)
        self.timer.start(900000)  # 15 minutos = 900000 ms
    
    def obtener_precios(self, pais):
        self.pais_actual = pais
        self.actualizar_precios()
    
    def actualizar_precios(self):
        acciones = {
            "EEUU": ["AAPL:NASDAQ", "MSFT:NASDAQ", "META:NASDAQ", "GOOGL:NASDAQ", "AMZN:NASDAQ", "SPY:NYSE", "TSLA:NASDAQ", "BRK-B:NYSE", "NVDA:NASDAQ"],
            "Argentina": ["GGAL:BCBA", "YPFD:BCBA", "PAMP:BCBA", "BMA:BCBA", "IMV:BCBA", "CEPU:BCBA", "TGSU2:BCBA"],
            "Brasil": ["VALE:BVMF", "PETR4:BVMF", "ITUB4:BVMF", "BBDC4:BVMF", "EWZ:NYSE", "ABEV3:BVMF", "BBAS3:BVMF"]
        }
        
        if not hasattr(self, 'pais_actual') or self.pais_actual not in acciones:
            return
        
        self.thread = DataFetcher(self.pais_actual, acciones[self.pais_actual])
        self.thread.data_fetched.connect(self.actualizar_tabla)
        self.thread.alert_triggered.connect(self.enviar_alerta_telegram)
        self.thread.start()
    
    def actualizar_tabla(self, data):
        self.table.setRowCount(0)
        for accion, precio, tendencia, variacion in data:
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(accion))
            self.table.setItem(row_position, 1, QTableWidgetItem(precio))
            self.table.setItem(row_position, 2, QTableWidgetItem(tendencia))
            self.table.setItem(row_position, 3, QTableWidgetItem(variacion))
    
    def enviar_alerta_telegram(self, mensaje):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage?chat_id={TELEGRAM_CHAT_ID}&text={mensaje}"
        requests.get(url)
    
    def toggle_always_on_top(self):
        if self.pin_button.isChecked():
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        else:
            self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, False)
        self.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = StockApp()
    window.show()
    sys.exit(app.exec())

"""
Aplicación tkinter para iniciar y detener el procesamiento de documentos
utilizando Apache Tika y watchdog.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox

from watchdog.observers import Observer
from tika_processor import (
    start_tika_server,
    process_document,
    INPUT_DIR,
    ACCEPT_FORMAT,
    WatcherHandler
)


class RedirectText:
    """Redirige stdout y stderr a un widget de tkinter."""

    def __init__(self, widget):
        self.widget = widget

    def write(self, string):
        """Escribe un string en el widget."""
        self.widget.configure(state='normal')
        self.widget.insert(tk.END, string)
        self.widget.see(tk.END)
        self.widget.configure(state='disabled')

    def flush(self):
        """Método flush requerido para compatibilidad."""


class SistemaTika:
    """
    Clase que gestiona el servidor Apache Tika y el monitoreo de la carpeta de entrada.

    Esta clase permite iniciar y detener el servidor Tika, procesar archivos existentes
    en la carpeta de entrada y monitorear nuevos archivos utilizando watchdog.
    """
    def __init__(self):
        self.tika_process = None
        self.observer = None
        self.is_running = False

    def iniciar_proceso(self):
        """
        Inicia el servidor Tika, procesa archivos existentes 
        y empieza a monitorizar la carpeta.
        """
        if self.is_running:
            messagebox.showinfo("Info", "El sistema ya está en ejecución.")
            return

        # Iniciar servidor Tika
        self.tika_process = start_tika_server()
        if not self.tika_process:
            messagebox.showerror("Error", "No se pudo iniciar el servidor Tika.")
            return

        # Procesar archivos existentes
        print("📂 Procesando archivos existentes...")
        for input_file_name in os.listdir(INPUT_DIR):
            input_file_path = os.path.join(INPUT_DIR, input_file_name)
            if os.path.isfile(input_file_path):
                print(f"  - {input_file_name}")
                process_document(input_file_path, ACCEPT_FORMAT)

        # Iniciar monitor de carpeta
        event_handler = WatcherHandler()
        self.observer = Observer()
        self.observer.schedule(event_handler, path=INPUT_DIR, recursive=False)
        self.observer.start()

        self.is_running = True
        print("🔍 Monitoreando la carpeta de entrada...")

    def detener_proceso(self):
        """Detiene el monitor de la carpeta y el servidor Tika."""
        if not self.is_running:
            messagebox.showinfo("Info", "El sistema no está en ejecución.")
            return

        # Detener observador
        if self.observer:
            print("🛑 Deteniendo monitor de carpeta...")
            self.observer.stop()
            self.observer.join()
            self.observer = None

        # Detener Tika
        if self.tika_process:
            print("🛑 Deteniendo Apache Tika Server...")
            self.tika_process.terminate()
            self.tika_process = None

        self.is_running = False
        print("✅ Sistema detenido.")


class AplicacionTika:
    """
    Clase que gestiona la interfaz gráfica para iniciar y detener el procesamiento de documentos.

    Esta clase utiliza tkinter para crear una interfaz gráfica que permite al usuario
    interactuar con el sistema Apache Tika, iniciar el servidor, procesar documentos
    y monitorear una carpeta de entrada.
    """
    def __init__(self):
        self.sistema_tika = SistemaTika()

    def salir_aplicacion(self, ventana):
        """Cierra la aplicación de forma segura."""
        if self.sistema_tika.is_running:
            self.sistema_tika.detener_proceso()
        ventana.destroy()

    def main(self):
        """Función principal para lanzar la aplicación tkinter."""
        ventana = tk.Tk()
        ventana.title("Procesador de Documentos - Apache Tika Monitor")
        ventana.geometry('900x700')

        # Área de texto scrollable
        log_text = scrolledtext.ScrolledText(ventana, state='disabled', wrap='word')
        log_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Redirigir stdout y stderr a la ventana
        sys.stdout = RedirectText(log_text)
        sys.stderr = RedirectText(log_text)

        # Botones
        frame_botones = tk.Frame(ventana)
        frame_botones.pack(pady=10)

        btn_iniciar = tk.Button(
            frame_botones,
            text="🚀 Iniciar Sistema",
            command=lambda: threading.Thread(target=self.sistema_tika.iniciar_proceso).start()
        )
        btn_iniciar.pack(side=tk.LEFT, padx=5)

        btn_detener = tk.Button(
            frame_botones,
            text="🛑 Detener Sistema",
            command=self.sistema_tika.detener_proceso
        )
        btn_detener.pack(side=tk.LEFT, padx=5)

        btn_salir = tk.Button(
            frame_botones,
            text="❌ Salir",
            command=lambda: self.salir_aplicacion(ventana)
        )
        btn_salir.pack(side=tk.LEFT, padx=5)

        ventana.mainloop()


if __name__ == "__main__":
    app = AplicacionTika()
    app.main()

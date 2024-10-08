import tkinter as tk
from tkinter import filedialog, messagebox
import os
import pandas as pd
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import SpanSelector
import csv
import re

# Función para seleccionar la carpeta de salida
def seleccionar_carpeta():
    carpeta_seleccionada = filedialog.askdirectory()
    if carpeta_seleccionada:
        carpeta_var.set(carpeta_seleccionada)
        cargar_archivos_csv(carpeta_seleccionada)

# Función para cargar los archivos CSV de las subcarpetas
def cargar_archivos_csv(carpeta):
    archivos_csv = []

    def buscar_archivos_csv(directorio):
        for root, dirs, files in os.walk(directorio):
            for dir_name in dirs:
                subdir_path = os.path.join(root, dir_name)
                for file in os.listdir(subdir_path):
                    if file.endswith('.csv'):
                        relative_path = os.path.relpath(os.path.join(subdir_path, file), carpeta)
                        archivos_csv.append(relative_path)

    buscar_archivos_csv(carpeta)

    archivo_var.set("")  # Limpiar la selección anterior
    archivo_dropdown['menu'].delete(0, 'end')
    for archivo in archivos_csv:
        archivo_dropdown['menu'].add_command(label=archivo, command=tk._setit(archivo_var, archivo))

# Función para cargar y mostrar los datos desde un archivo CSV seleccionado
def cargar_archivo():
    archivo_seleccionado = archivo_var.get()
    carpeta = carpeta_var.get()
    
    if archivo_seleccionado:
        df = pd.read_csv(os.path.join(carpeta, archivo_seleccionado))
        
        x = df.columns[0]
        y = df.columns[1]
        
        x = df[x].values
        y = df[y].values
        
        ax1.clear()
        ax1.plot(x, y)
        
        y_min = min(y) - 5
        y_max = max(y) + 5
        
        ax1.set_ylim(y_min, y_max)
        ax1.set_title(f'Selected file: {archivo_seleccionado}')
        
        global x_global, y_global
        x_global = x
        y_global = y
        
        # Calcular y mostrar el piso de ruido con formato específico
        media = np.mean(y)
        media_str = f"{media:.3f} dB"
        
        # Limpiar la leyenda anterior y añadir la nueva
        ax1.get_legend().remove() if ax1.get_legend() else None
        ax1.axhline(y=media, color='red', linestyle='--', label=f'Noise floor: {media_str}')
        ax1.legend(loc='upper right')  # Puedes ajustar la posición de la leyenda si lo deseas
        canvas.draw()

# Función para manejar la selección de una región
def onselect(xmin, xmax):
    indmin, indmax = np.searchsorted(x_global, (xmin, xmax))
    indmax = min(len(x_global) - 1, indmax)

    region_x = x_global[indmin:indmax]
    region_y = y_global[indmin:indmax]

    if len(region_x) >= 2:
        ax2.clear()
        ax2.plot(region_x, region_y)
        ax2.set_xlim(region_x[0], region_x[-1])
        ax2.set_ylim((region_y.min()-5), (region_y.max()+5))
        
        setpoint_str = setpoint_entry.get()
        if setpoint_str:
            try:
                setpoint = float(setpoint_str)
                encontrar_maximos(setpoint, ax2)
            except ValueError:
                pass  # Si no es un número válido, solo ignorar
        canvas.draw()

# Función para encontrar y mostrar máximos por encima de un setpoint
def encontrar_maximos(setpoint, axis):
    global x_global, y_global
    
    if len(x_global) == 0 or len(y_global) == 0:
        return
    
    maximos = []
    for i, valor in enumerate(y_global):
        if valor > setpoint:
            maximos.append((x_global[i], valor))
    
    if maximos:
        x_maximos, y_maximos = zip(*maximos)
        
        # Limpiar la leyenda anterior y añadir los nuevos máximos
        axis.get_legend().remove() if axis.get_legend() else None
        axis.plot(x_maximos, y_maximos, 'go', label=f'Reference level > {setpoint} dB')
        axis.legend(loc='upper right')  # Puedes ajustar la posición de la leyenda si lo deseas
        canvas.draw()

# Función para guardar los máximos encontrados en un archivo CSV cuando se presiona "Generar Reporte"
def guardar_reporte():
    setpoint_str = setpoint_entry.get()
    if not setpoint_str:
        messagebox.showerror("Error", "The setpoint field is empty. Please enter a numeric value.")
        return

    try:
        setpoint = float(setpoint_str)
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid numeric value for the setpoint.")
        return

    global x_global, y_global
    
    if len(x_global) == 0 or len(y_global) == 0:
        messagebox.showerror("Error", "There is no data to generate the report.")
        return
    
    maximos = []
    for i, valor in enumerate(y_global):
        if valor > setpoint:
            maximos.append((x_global[i], valor))
    
    if not maximos:
        messagebox.showinfo("Information", f"No maximums were found above the setpoint {setpoint} dB.")
        return
    
    nombre_archivo = archivo_var.get()
    if not nombre_archivo:
        messagebox.showerror("Error", "No file has been selected.")
        return
    
    nombre_base = os.path.basename(nombre_archivo)
    
    # Construir el nombre del reporte 
    nombre_reporte = f"Reporte_{nombre_base}"
    
    carpeta_archivo = os.path.dirname(os.path.join(carpeta_var.get(), nombre_archivo))
    guardar_path = os.path.join(carpeta_archivo, nombre_reporte)

    # Construir los datos del reporte
    media = np.mean(y_global)
    reporte = []
    reporte.append(f"File Report: {nombre_archivo}")
    reporte.append(f"Noise Floor: {media:.3f} dB")
    reporte.append(f"Setpoint: {setpoint} dB")
    reporte.append("--- Maximum Values Above the Setpoint: ---")
    reporte.append("Frequency (MHz), dB")
    
    for freq, db in maximos:
        reporte.append(f"{freq:.2f}, {db:.2f}")
    
    try:
        with open(guardar_path, 'w', newline='') as file:
            writer = csv.writer(file)
            for line in reporte:
                writer.writerow([line])
        messagebox.showinfo("Saved", f"Report successfully saved to:\n{guardar_path}")
    except Exception as e:
        messagebox.showerror("Error", f"The report could not be saved.\nError: {str(e)}")

# Función para actualizar el setpoint desde la interfaz gráfica
def actualizar_setpoint():
    try:
        nuevo_setpoint = float(setpoint_entry.get())
        encontrar_maximos(nuevo_setpoint, ax1)
        onselect(ax2.get_xlim()[0], ax2.get_xlim()[1])  # Actualizar gráfica de detalle
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid numerical value for the setpoint.")

def main():
    global root, carpeta_var, archivo_var, archivo_dropdown, ax1, ax2, canvas, x_global, y_global, setpoint_entry

    root = tk.Tk()
    root.title("Visualization and Report")

    ancho_ventana = 1000
    alto_ventana = 800
    posicion_x = (root.winfo_screenwidth() // 2) - (ancho_ventana // 2)
    posicion_y = (root.winfo_screenheight() // 2) - (alto_ventana // 2)
    root.geometry(f"{ancho_ventana}x{alto_ventana}+{posicion_x}+{posicion_y}")

    seleccionar_carpeta_button = tk.Button(root, text="Select Folder", command=seleccionar_carpeta)
    seleccionar_carpeta_button.pack()

    carpeta_var = tk.StringVar(root)
    archivo_var = tk.StringVar(root)

    archivo_dropdown = tk.OptionMenu(root, archivo_var, "")
    archivo_dropdown.pack()

    cargar_button = tk.Button(root, text="Generate Graph", command=cargar_archivo)
    cargar_button.pack()

    setpoint_label = tk.Label(root, text="Setpoint:")
    setpoint_label.pack()

    setpoint_entry = tk.Entry(root)
    setpoint_entry.pack()

    actualizar_setpoint_button = tk.Button(root, text="Update Setpoint", command=actualizar_setpoint)
    actualizar_setpoint_button.pack()

    generar_reporte_button = tk.Button(root, text="Generate Report", command=guardar_reporte)
    generar_reporte_button.pack()

    fig = Figure(figsize=(18, 12))
    ax1 = fig.add_subplot(211)
    ax2 = fig.add_subplot(212)

    canvas = FigureCanvasTkAgg(fig, master=root)
    canvas.draw()
    canvas.get_tk_widget().pack()

    span = SpanSelector(
        ax1,
        onselect,
        "horizontal",
        useblit=True,
        props=dict(alpha=0.5, facecolor="tab:blue"),
        interactive=True,
        drag_from_anywhere=True
    )

    x_global = []
    y_global = []

    root.mainloop()

if __name__ == "__main__":
    main()
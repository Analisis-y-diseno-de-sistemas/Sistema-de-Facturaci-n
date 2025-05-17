import tkinter as tk
from tkinter import messagebox, ttk
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import sys

# 1. Configuración inicial y carga de datos
try:
    # Carga de datos
    df_c = pd.read_excel("base_de_datos.xlsx", sheet_name="CLIENTES")
    df_p = pd.read_excel("base_de_datos.xlsx", sheet_name="PRODUCTOS")

    # Conversión segura de códigos a texto
    df_p['CODIGO'] = df_p['CODIGO'].astype(str).str.strip()
    df_c['NIT'] = df_c['NIT'].astype(str).str.strip()
    df_c['NOMBRE'] = df_c['NOMBRE'].astype(str).str.strip()

    # Limpieza de datos
    df_c = df_c[~df_c['NOMBRE'].isin(['', 'nan', 'None'])]
    df_p = df_p[~df_p['CODIGO'].isin(['', 'nan', 'None'])]

except Exception as e:
    messagebox.showerror("Error", f"Error al cargar datos:\n{str(e)}")
    sys.exit()

# Variables globales
entry_cantidad = []
entry_busqueda = None
productos_mostrados = pd.DataFrame()
CODIGO_COLUMN = "CODIGO"
PRODUCTO_COLUMN = "PRODUCTO"
PRECIO_COLUMN = "PRECIO UNITARIO"
carrito=[]


# 2. Función para generar PDF corregida
def generar_pdf(cliente, productos, total):
    try:
        nombre_archivo = f"Factura_{cliente['NIT']}.pdf"

        # Crear canvas correctamente
        c = canvas.Canvas(nombre_archivo, pagesize=letter)

        # Encabezado
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "FACTURA")
        c.setFont("Helvetica", 12)
        c.drawString(100, 725, f"Cliente: {cliente['NOMBRE']}")
        c.drawString(100, 705, f"NIT: {cliente['NIT']}")
        if 'DIRECCION' in cliente:
            c.drawString(100, 685, f"Dirección: {cliente['DIRECCION']}")

        # Detalles de productos
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 650, "CÓDIGO")
        c.drawString(150, 650, "DESCRIPCIÓN")
        c.drawString(350, 650, "CANT.")
        c.drawString(400, 650, "PRECIO UNIT.")
        c.drawString(500, 650, "TOTAL")

        y_position = 630
        c.setFont("Helvetica", 10)
        for prod, cantidad, subtotal in productos:
            c.drawString(50, y_position, str(prod[CODIGO_COLUMN]))
            c.drawString(150, y_position, str(prod[PRODUCTO_COLUMN])[:30])
            c.drawString(350, y_position, str(int(cantidad) if cantidad.is_integer() else cantidad))
            c.drawString(400, y_position, f"Q{prod[PRECIO_COLUMN]:.2f}")
            c.drawString(500, y_position, f"Q{subtotal:.2f}")
            y_position -= 20

        # Total
        c.setFont("Helvetica-Bold", 14)
        c.drawString(400, y_position - 30, f"TOTAL: Q{total:.2f}")

        c.save()
        messagebox.showinfo("Éxito", f"Factura generada:\n{nombre_archivo}")
    except Exception as e:
        messagebox.showerror("Error PDF", f"No se pudo generar el PDF:\n{str(e)}")


# 3. Búsqueda y visualización de productos corregida
def buscar_productos(event=None):
    global productos_mostrados, entry_cantidad

    codigo = entry_busqueda.get().strip()

    # Limpiar widgets anteriores
    for widget in frame_productos.winfo_children():
        widget.destroy()
    entry_cantidad = []

    if not codigo:
        return

    try:
        # Búsqueda insensible a mayúsculas/espacios
        productos_mostrados = df_p[
            df_p[CODIGO_COLUMN].astype(str).str.upper().str.contains(codigo.upper())
        ].copy()

        if productos_mostrados.empty:
            messagebox.showinfo("Búsqueda", "No se encontraron productos")
            return

        # Mostrar encabezados
        tk.Label(frame_productos, text="Código", font=('Arial', 10, 'bold')).grid(row=0, column=0, padx=5)
        tk.Label(frame_productos, text="Producto", font=('Arial', 10, 'bold')).grid(row=0, column=1, padx=5)
        tk.Label(frame_productos, text="Precio Unit.", font=('Arial', 10, 'bold')).grid(row=0, column=2, padx=5)
        tk.Label(frame_productos, text="Cantidad", font=('Arial', 10, 'bold')).grid(row=0, column=3, padx=5)

        # Mostrar resultados
        for i, (_, row) in enumerate(productos_mostrados.iterrows(), 1):
            tk.Label(frame_productos, text=row[CODIGO_COLUMN], font=('Arial', 10)).grid(row=i, column=0)
            tk.Label(frame_productos, text=row[PRODUCTO_COLUMN], font=('Arial', 10)).grid(row=i, column=1)
            tk.Label(frame_productos, text=f"Q{row[PRECIO_COLUMN]:.2f}", font=('Arial', 10)).grid(row=i, column=2)

            entry = tk.Entry(frame_productos, font=('Arial', 10), justify='center')
            entry.insert(0, "0")
            entry.grid(row=i, column=3, ipady=3)
            entry_cantidad.append(entry)

    except Exception as e:
        messagebox.showerror("Error", f"Error en búsqueda:\n{str(e)}")

# AGREGAR A CARRITO
def agregar_a_carrito():
    global carrito

    if productos_mostrados.empty:
        messagebox.showerror("Error", "Primero busca un producto")
        return

    agregado = False

    for i, entry in enumerate(entry_cantidad):
        try:
            cantidad = float(entry.get())
            if cantidad <= 0:
                continue

            producto = productos_mostrados.iloc[i]
            subtotal = cantidad * producto[PRECIO_COLUMN]

            # Añadir al carrito
            carrito.append((producto, cantidad, subtotal))

            # Mostrar en tabla
            tree.insert("", "end", values=(
                producto[CODIGO_COLUMN],
                producto[PRODUCTO_COLUMN],
                cantidad,
                f"Q{producto[PRECIO_COLUMN]:.2f}",
                f"Q{subtotal:.2f}"
            ))

            agregado = True

        except ValueError:
            continue

    if not agregado:
        messagebox.showinfo("Aviso", "Ingrese al menos una cantidad válida mayor a 0")


# 4. Generación de factura corregida
def generar_factura():
    try:
        cliente = cb_cliente.get()
        if cliente == "Seleccionar Cliente":
            messagebox.showerror("Error", "Seleccione un cliente válido")
            return

        if not carrito:
            messagebox.showerror("ERROR", "No hay productos en la factura")
            return

        productos_seleccionados = carrito.copy()
        total = sum(item[2] for item in productos_seleccionados)

        cliente_info = df_c[df_c['NOMBRE'] == cliente].iloc[0]
        generar_pdf(cliente_info, productos_seleccionados, total)

    except Exception as e:
        messagebox.showerror("Error", f"Error al facturar:\n{str(e)}")


# 5. Interfaz gráfica
root = tk.Tk()
root.title("Sistema de Facturación")
root.geometry("1000x700")

# Marco principal
main_frame = tk.Frame(root, bg='#f0f0f0')
main_frame.pack(pady=20, padx=20, fill='both', expand=True)

# Sección cliente
tk.Label(main_frame, text="Cliente:", font=('Arial', 12), bg='#f0f0f0').grid(row=0, column=0, sticky='w', pady=5)
nombres_clientes = sorted(df_c['NOMBRE'].unique().tolist(), key=lambda x: str(x).lower())
cb_cliente = ttk.Combobox(
    main_frame,
    values=["Seleccionar Cliente"] + nombres_clientes,
    font=('Arial', 12),
    state='readonly'
)
cb_cliente.grid(row=0, column=1, padx=10, pady=5, sticky='ew')
cb_cliente.current(0)

# Sección búsqueda
tk.Label(main_frame, text="Buscar por código:", font=('Arial', 12), bg='#f0f0f0').grid(row=1, column=0, sticky='w',
                                                                                       pady=5)
entry_busqueda = tk.Entry(main_frame, font=('Arial', 12))
entry_busqueda.grid(row=1, column=1, padx=10, pady=5, sticky='ew')
entry_busqueda.bind('<Return>', buscar_productos)
btn_buscar = tk.Button(
    main_frame,
    text="Buscar",
    command=buscar_productos,
    font=('Arial', 12),
    bg='#4CAF50',
    fg='white'
)
btn_buscar.grid(row=1, column=2, padx=10, ipadx=20)

btn_agregar = tk.Button(
    main_frame,
    text="Agregar a la factura",
    command=agregar_a_carrito,
    font=('Arial', 12),
    bg='#009688',
    fg='white'
)
btn_agregar.grid(row=1, column=3, padx=10, ipadx=10)

# Área de productos con scroll
frame_container = tk.Frame(main_frame, bg='#f0f0f0')
frame_container.grid(row=2, column=0, columnspan=3, sticky='nsew', pady=10)

canvvas = tk.Canvas(frame_container, bg='white', highlightthickness=0)
scrollbar = ttk.Scrollbar(frame_container, orient='vertical', command=canvvas.yview)
frame_productos = tk.Frame(canvvas, bg='white')

frame_productos.bind('<Configure>', lambda e: canvvas.configure(scrollregion=canvvas.bbox('all')))
canvvas.create_window((0, 0), window=frame_productos, anchor='nw')
canvvas.configure(yscrollcommand=scrollbar.set)

canvvas.pack(side='left', fill='both', expand=True)
scrollbar.pack(side='right', fill='y')

#TABLA CARRITO
tk.Label(main_frame, text="Productos en la factura:", font=('Arial', 12, 'bold')).grid(row=3, column=0, columnspan=3, pady=(10, 0), sticky='w')

tree = ttk.Treeview(main_frame, columns=("codigo", "producto", "cantidad", "precio", "subtotal"), show="headings", height=8)
tree.grid(row=4, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

for col, ancho in zip(["codigo", "producto", "cantidad", "precio", "subtotal"], [100, 250, 80, 100, 100]):
    tree.heading(col, text=col.capitalize())
    tree.column(col, width=ancho)



# Botón factura
btn_facturar = tk.Button(
    main_frame,
    text="Generar Factura PDF",
    command=generar_factura,
    font=('Arial', 14, 'bold'),
    bg='#2196F3',
    fg='white',
    padx=20,
    pady=10
)
btn_facturar.grid(row=3, column=0, columnspan=3, pady=20)

# Configuración de redimensionamiento
main_frame.columnconfigure(1, weight=1)
main_frame.rowconfigure(2, weight=1)

root.mainloop()
import tkinter as tk
from tkinter import messagebox, ttk
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import sys
import os  # Importar para verificar existencia de archivos de imagen

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

# Uso en tu código:
df_c = pd.read_excel(resource_path("base_de_datos.xlsx"), sheet_name="CLIENTES")
    
# --- 1. Configuración inicial y carga de datos ---
try:
    # Carga de datos
    df_c = pd.read_excel("base_de_datos.xlsx", sheet_name="CLIENTES")
    df_p = pd.read_excel("base_de_datos.xlsx", sheet_name="PRODUCTOS")

    # Conversión segura de códigos a texto
    df_p['CODIGO'] = df_p['CODIGO'].astype(str).str.strip()
    df_c['NIT'] = df_c['NIT'].astype(str).str.strip()
    df_c['NOMBRE'] = df_c['NOMBRE'].astype(str).str.strip()

    # Limpieza de datos (eliminar filas con valores vacíos o 'nan' en columnas clave)
    df_c = df_c[~df_c['NOMBRE'].isin(['', 'nan', 'None'])]
    df_p = df_p[~df_p['CODIGO'].isin(['', 'nan', 'None'])]

except FileNotFoundError:
    messagebox.showerror("Error de Archivo",
                         "Asegúrate de que 'base_de_datos.xlsx' esté en la misma carpeta que el script.")
    sys.exit()
except Exception as e:
    messagebox.showerror("Error", f"Error al cargar datos: {str(e)}")
    sys.exit()

# Variables globales
entry_cantidad = []  # Lista de Entry widgets para cantidades de productos mostrados
entry_busqueda = None
productos_mostrados = pd.DataFrame()  # DataFrame de los productos que se muestran en la búsqueda
CODIGO_COLUMN = "CODIGO"
PRODUCTO_COLUMN = "PRODUCTO"
PRECIO_COLUMN = "PRECIO UNITARIO"
carrito = []  # Lista de tuplas: (producto_dict, cantidad, subtotal)
total_factura_var = None  # Variable para el total mostrado en la interfaz
status_bar = None  # Etiqueta para la barra de estado


# --- Funciones auxiliares ---
def actualizar_total_factura():
    """Actualiza el total de la factura mostrado en la interfaz."""
    total = sum(item[2] for item in carrito)
    total_factura_var.set(f"Total: Q{total:.2f}")


def mostrar_mensaje_estado(mensaje, tipo="info"):
    """Muestra un mensaje en la barra de estado."""
    if status_bar:
        status_bar.config(text=mensaje, fg='black')  # Color por defecto
        if tipo == "error":
            status_bar.config(fg='red')
        elif tipo == "success":
            status_bar.config(fg='green')
        # Puedes añadir un temporizador para que el mensaje desaparezca después de unos segundos
        # root.after(5000, lambda: status_bar.config(text="")) # Descomentar para auto-borrar


# --- 2. Función para generar PDF ---
def generar_pdf(cliente, productos, total):
    try:
        nombre_archivo = f"Factura_{cliente['NIT']}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        c = canvas.Canvas(nombre_archivo, pagesize=letter)

        # Encabezado
        c.setFont("Helvetica-Bold", 16)
        c.drawString(100, 750, "FACTURA DE VENTA")
        c.setFont("Helvetica", 12)
        c.drawString(100, 725, f"Cliente: {cliente['NOMBRE']}")
        c.drawString(100, 705, f"NIT: {cliente['NIT']}")
        if 'DIRECCION' in cliente and pd.notna(cliente['DIRECCION']):
            c.drawString(100, 685, f"Dirección: {cliente['DIRECCION']}")
        c.drawString(100, 665, f"Fecha: {pd.Timestamp.now().strftime('%d/%m/%Y %H:%M')}")

        # Detalles de productos
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 630, "CÓDIGO")
        c.drawString(150, 630, "DESCRIPCIÓN")
        c.drawString(350, 630, "CANT.")
        c.drawString(400, 630, "PRECIO UNIT.")
        c.drawString(500, 630, "TOTAL")

        y_position = 610
        c.setFont("Helvetica", 10)
        for prod_info, cantidad, subtotal in productos:
            # prod_info es un objeto Series de Pandas, accedemos como diccionario
            c.drawString(50, y_position, str(prod_info[CODIGO_COLUMN]))
            c.drawString(150, y_position, str(prod_info[PRODUCTO_COLUMN])[:35])  # Limitar longitud
            c.drawString(350, y_position, str(int(cantidad) if cantidad == int(cantidad) else f"{cantidad:.2f}"))
            c.drawString(400, y_position, f"Q{prod_info[PRECIO_COLUMN]:.2f}")
            c.drawString(500, y_position, f"Q{subtotal:.2f}")
            y_position -= 18  # Ajustar espaciado

            if y_position < 100:  # Nueva página si se acerca al final
                c.showPage()
                c.setFont("Helvetica-Bold", 12)
                c.drawString(50, 750, "CÓDIGO")
                c.drawString(150, 750, "DESCRIPCIÓN")
                c.drawString(350, 750, "CANT.")
                c.drawString(400, 750, "PRECIO UNIT.")
                c.drawString(500, 750, "TOTAL")
                y_position = 730
                c.setFont("Helvetica", 10)

        # Total
        c.setFont("Helvetica-Bold", 14)
        c.drawString(400, y_position - 30, f"TOTAL: Q{total:.2f}")

        c.save()
        messagebox.showinfo("Éxito", f"Factura generada:\n{nombre_archivo}")
        mostrar_mensaje_estado(f"Factura '{nombre_archivo}' generada con éxito.", "success")
        limpiar_carrito_y_campos()  # Limpiar después de facturar

    except Exception as e:
        messagebox.showerror("Error PDF", f"No se pudo generar el PDF: {str(e)}")
        mostrar_mensaje_estado(f"Error al generar PDF: {str(e)}", "error")


# --- 3. Búsqueda y visualización de productos ---
def buscar_productos(event=None):
    global productos_mostrados, entry_cantidad

    codigo_o_nombre = entry_busqueda.get().strip()

    # Limpiar widgets anteriores
    for widget in frame_productos.winfo_children():
        widget.destroy()
    entry_cantidad = []

    if not codigo_o_nombre:
        productos_mostrados = pd.DataFrame()  # Limpiar resultados si la búsqueda está vacía
        mostrar_mensaje_estado("Ingrese un código o nombre para buscar productos.", "info")
        return

    try:
        # Búsqueda insensible a mayúsculas/espacios en CODIGO y PRODUCTO
        productos_mostrados = df_p[
            df_p[CODIGO_COLUMN].astype(str).str.upper().str.contains(codigo_o_nombre.upper()) |
            df_p[PRODUCTO_COLUMN].astype(str).str.upper().str.contains(codigo_o_nombre.upper())
            ].copy()

        if productos_mostrados.empty:
            messagebox.showinfo("Búsqueda", f"No se encontraron productos para '{codigo_o_nombre}'")
            mostrar_mensaje_estado(f"No se encontraron productos para '{codigo_o_nombre}'", "info")
            return

        # Mostrar encabezados
        tk.Label(frame_productos, text="Código", font=('Arial', 10, 'bold'), bg='white').grid(row=0, column=0, padx=5,
                                                                                              pady=2)
        tk.Label(frame_productos, text="Producto", font=('Arial', 10, 'bold'), bg='white').grid(row=0, column=1, padx=5,
                                                                                                pady=2)
        tk.Label(frame_productos, text="Precio Unit.", font=('Arial', 10, 'bold'), bg='white').grid(row=0, column=2,
                                                                                                    padx=5, pady=2)
        tk.Label(frame_productos, text="Cantidad", font=('Arial', 10, 'bold'), bg='white').grid(row=0, column=3, padx=5,
                                                                                                pady=2)

        # Mostrar resultados
        for i, (_, row) in enumerate(productos_mostrados.iterrows(), 1):
            tk.Label(frame_productos, text=row[CODIGO_COLUMN], font=('Arial', 10), bg='white').grid(row=i, column=0,
                                                                                                    sticky='w')
            tk.Label(frame_productos, text=row[PRODUCTO_COLUMN], font=('Arial', 10), bg='white').grid(row=i, column=1,
                                                                                                      sticky='w')
            tk.Label(frame_productos, text=f"Q{row[PRECIO_COLUMN]:.2f}", font=('Arial', 10), bg='white').grid(row=i,
                                                                                                              column=2,
                                                                                                              sticky='e')

            entry = tk.Entry(frame_productos, font=('Arial', 10), justify='center', width=10)
            entry.insert(0, "0")
            entry.grid(row=i, column=3, ipady=3, padx=5)
            entry_cantidad.append(entry)

        mostrar_mensaje_estado(f"Productos encontrados: {len(productos_mostrados)}", "info")
        # Ajustar el scrollregion después de añadir los widgets
        frame_productos.update_idletasks()  # Asegurarse de que los widgets se dibujen
        canvvas.config(scrollregion=canvvas.bbox("all"))


    except Exception as e:
        messagebox.showerror("Error", f"Error en búsqueda: {str(e)}")
        mostrar_mensaje_estado(f"Error en búsqueda: {str(e)}", "error")


# --- AGREGAR A CARRITO ---
def agregar_a_carrito():
    global carrito

    if productos_mostrados.empty:
        messagebox.showerror("Error", "Primero busca un producto para agregar.")
        mostrar_mensaje_estado("No hay productos buscados para agregar.", "error")
        return

    agregado = False
    productos_a_agregar = []

    for i, entry in enumerate(entry_cantidad):
        try:
            cantidad_str = entry.get().strip()
            if not cantidad_str:  # Si el campo está vacío, asumir 0
                cantidad = 0.0
            else:
                cantidad = float(cantidad_str)

            if cantidad <= 0:
                continue

            producto = productos_mostrados.iloc[i]
            subtotal = cantidad * producto[PRECIO_COLUMN]

            productos_a_agregar.append((producto, cantidad, subtotal))
            agregado = True

        except ValueError:
            messagebox.showerror("Error de Cantidad",
                                 f"Cantidad '{entry.get()}' no válida para el producto {productos_mostrados.iloc[i][PRODUCTO_COLUMN]}. Ingrese un número.")
            mostrar_mensaje_estado(f"Cantidad no válida para {productos_mostrados.iloc[i][PRODUCTO_COLUMN]}", "error")
            return  # Detener si hay un error en una cantidad

    if not agregado:
        messagebox.showinfo("Aviso", "Ingrese una cantidad válida (mayor a 0) para al menos un producto.")
        mostrar_mensaje_estado("No se ingresó ninguna cantidad válida.", "info")
        return

    # Añadir al carrito y actualizar tabla solo si no hubo errores
    for prod, cant, sub in productos_a_agregar:
        carrito.append((prod, cant, sub))
        tree.insert("", "end", values=(
            prod[CODIGO_COLUMN],
            prod[PRODUCTO_COLUMN],
            int(cant) if cant == int(cant) else f"{cant:.2f}",  # Formato de cantidad
            f"Q{prod[PRECIO_COLUMN]:.2f}",
            f"Q{sub:.2f}"
        ))

    mostrar_mensaje_estado("Producto(s) agregado(s) a la factura.", "success")
    actualizar_total_factura()
    entry_busqueda.delete(0, tk.END)  # Limpiar campo de búsqueda
    for entry in entry_cantidad:  # Limpiar campos de cantidad
        entry.delete(0, tk.END)
        entry.insert(0, "0")
    buscar_productos()  # Limpiar productos mostrados


# --- Funciones para el Carrito ---
def eliminar_del_carrito():
    global carrito
    selected_items = tree.selection()
    if not selected_items:
        messagebox.showinfo("Eliminar", "Seleccione un producto del carrito para eliminar.")
        mostrar_mensaje_estado("Seleccione un ítem para eliminar.", "info")
        return

    for item in selected_items:
        index = tree.index(item)
        if 0 <= index < len(carrito):
            carrito.pop(index)
            tree.delete(item)
            mostrar_mensaje_estado("Producto eliminado del carrito.", "info")
    actualizar_total_factura()


def limpiar_carrito_y_campos():
    global carrito
    carrito.clear()
    for item in tree.get_children():
        tree.delete(item)
    actualizar_total_factura()
    entry_busqueda.delete(0, tk.END)
    for entry in entry_cantidad:
        entry.delete(0, tk.END)
        entry.insert(0, "0")
    buscar_productos()  # Limpiar el área de productos buscados

    mostrar_mensaje_estado("Carrito y campos de búsqueda limpiados.", "info")


# --- 4. Generación de factura ---
def generar_factura():
    try:
        cliente_nombre = entry_cliente.get().strip()
        cliente_nit = entry_nit.get().strip()
        if not cliente_nombre:
            messagebox.showerror("Error", "Ingrese nombre de cliente antes de facturar.")
            mostrar_mensaje_estado("Error: Nombre de cliente vacio.", "error")
            return

        if not cliente_nit:
            respuesta = messagebox.askyesno("NIT vacío", "No se ingreso NIT ¿desea usar CF?")
            if not respuesta:
                return
            cliente_nit = "CF"

        if not carrito:
            messagebox.showerror("ERROR", "No hay productos en la factura para generar el PDF.")
            mostrar_mensaje_estado("Error: Carrito vacío.", "error")
            return

        total = sum(item[2] for item in carrito)

        cliente_info = {
            'NOMBRE': cliente_nombre,
            'NIT': cliente_nit,
            'DIRECCION': entry_direccion.get().strip() if entry_direccion.get().strip() else 'No especificada'
        }
        # Generar nombre de archivo seguro
        nombre_archivo = f"Factura_{cliente_nit}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        # Validar nombre de archivo
        nombre_archivo = "".join(c for c in nombre_archivo if c.isalnum() or c in ('_', '-', '.'))
        generar_pdf(cliente_info, carrito, total)


    except Exception as e:
        messagebox.showerror("Error", f"Error al intentar facturar: {str(e)}")
        mostrar_mensaje_estado(f"Error al intentar facturar: {str(e)}", "error")

# --- Función para buscar cliente existente ---
def buscar_cliente():
    cliente_busqueda = entry_cliente.get().strip()
    if not cliente_busqueda:
        messagebox.showinfo("Búsqueda", "Ingrese un nombre para buscar cliente.")
        return

    clientes_coincidentes = df_c[df_c['NOMBRE'].str.upper().str.contains(cliente_busqueda.upper())]

    if clientes_coincidentes.empty:
        messagebox.showinfo("Búsqueda", f"No se encontraron clientes con '{cliente_busqueda}'")
        return

    # Crear ventana emergente para seleccionar cliente
    popup = tk.Toplevel(root)
    popup.title("Seleccionar Cliente")
    popup.geometry("500x300")

    tk.Label(popup, text="Clientes encontrados:", font=('Arial', 12)).pack(pady=5)

    columns = ('nombre', 'nit', 'direccion')
    tree_clientes = ttk.Treeview(popup, columns=columns, show='headings', height=8)

    tree_clientes.heading('nombre', text='Nombre')
    tree_clientes.heading('nit', text='NIT')
    tree_clientes.heading('direccion', text='Dirección')

    tree_clientes.column('nombre', width=200)
    tree_clientes.column('nit', width=100)
    tree_clientes.column('direccion', width=250)

    for _, row in clientes_coincidentes.iterrows():
        tree_clientes.insert('', tk.END, values=(row['NOMBRE'], row['NIT'], row.get('DIRECCION', '')))

    tree_clientes.pack(pady=5, padx=10, fill='both', expand=True)

    def seleccionar_cliente():
        seleccion = tree_clientes.selection()
        if seleccion:
            valores = tree_clientes.item(seleccion[0], 'values')
            entry_cliente.delete(0, tk.END)
            entry_cliente.insert(0, valores[0])
            entry_nit.delete(0, tk.END)
            entry_nit.insert(0, valores[1])
            if len(valores) > 2:
                entry_direccion.delete(0, tk.END)
                entry_direccion.insert(0, valores[2])
            popup.destroy()

    btn_seleccionar = tk.Button(popup, text="Seleccionar", command=seleccionar_cliente)
    btn_seleccionar.pack(pady=5)



# --- 5. Interfaz gráfica ---
root = tk.Tk()
root.title("Sistema de Facturación")
root.geometry("1100x800")  # Aumenté un poco el tamaño para los nuevos campos
root.option_add('*tearOff', False)

# Marco principal
main_frame = tk.Frame(root, bg='#f0f0f0', padx=15, pady=15, bd=2, relief='groove')
main_frame.pack(pady=10, padx=10, fill='both', expand=True)

# --- Sección de datos del cliente ---
frame_cliente = tk.LabelFrame(main_frame, text="Datos del Cliente", font=('Arial', 12, 'bold'), bg='#f0f0f0', padx=10, pady=10)
frame_cliente.grid(row=0, column=0, columnspan=4, sticky='ew', pady=5   )


# Nombre del cliente
tk.Label(frame_cliente, text="Nombre del Cliente:", font=('Arial', 11, 'bold'), bg='#f0f0f0').grid(row=0, column=0, sticky='w', padx=5)
entry_cliente = tk.Entry(frame_cliente, font=('Arial', 11), bd=2, relief='sunken', width=40)
entry_cliente.grid(row=0, column=1, padx=5, pady=2, sticky='w')

# NIT del cliente
tk.Label(frame_cliente, text="NIT:", font=('Arial', 11, 'bold'), bg='#f0f0f0').grid(row=1, column=0, sticky='w', padx=5)
entry_nit = tk.Entry(frame_cliente, font=('Arial', 11), bd=2, relief='sunken', width=20)
entry_nit.grid(row=1, column=1, padx=5, pady=2, sticky='w')

# Dirección (opcional)
tk.Label(frame_cliente, text="Dirección:", font=('Arial', 11, 'bold'), bg='#f0f0f0').grid(row=2, column=0, sticky='w', padx=5)
entry_direccion = tk.Entry(frame_cliente, font=('Arial', 11), bd=2, relief='sunken', width=40)
entry_direccion.grid(row=2, column=1, padx=5, pady=2, sticky='w')

# Botón para buscar cliente existente
btn_buscar_cliente = tk.Button(
    frame_cliente,
    text=" Buscar Cliente Existente",
    compound='left',
    command=buscar_cliente,
    font=('Arial', 10),
    bg='#6c757d',
    fg='white',
    activebackground='#6c757d',
    activeforeground='white',
    cursor="hand2"
)
btn_buscar_cliente.grid(row=0, column=2, rowspan=2, padx=10, pady=2, ipadx=5, ipady=5, sticky='w')

# --- Cargar imágenes para botones (Si existen) ---
# Asegúrate de tener estas imágenes en la misma carpeta o proporciona la ruta completa
icon_search_img = None
icon_add_img = None
icon_delete_img = None
icon_bill_img = None
icon_clear_img = None
icon_client_search_img = None

try:
    if os.path.exists("icons/search.png"): icon_search_img = tk.PhotoImage(file="icons/search.png")
    if os.path.exists("icons/add.png"): icon_add_img = tk.PhotoImage(file="icons/add.png")
    if os.path.exists("icons/delete.png"): icon_delete_img = tk.PhotoImage(file="icons/delete.png")
    if os.path.exists("icons/bill.png"): icon_bill_img = tk.PhotoImage(file="icons/bill.png")
    if os.path.exists("icons/clear.png"): icon_clear_img = tk.PhotoImage(file="icons/clear.png")
    if os.path.exists("icons/client_search.png"): icon_client_search_img = tk.PhotoImage(file="icons/client_search.png")
except Exception as e:
    print(f"Error cargando íconos: {e}")
    # Si hay error, los botones se mostrarán solo con texto.


# Sección búsqueda de productos
tk.Label(main_frame, text="Buscar producto (código/nombre):", font=('Arial', 12, 'bold'), bg='#f0f0f0').grid(row=1, column=0, sticky='w', pady=5, padx=5)

entry_busqueda = tk.Entry(main_frame, font=('Arial', 11), bd=2, relief='sunken')
entry_busqueda.grid(row=1, column=1, padx=10, pady=5, sticky='ew')
entry_busqueda.bind('<Return>', buscar_productos)  # Búsqueda al presionar Enter

btn_buscar = tk.Button(
    main_frame,
    text=" Buscar",
    image=icon_search_img,
    compound='left',  # Coloca el texto a la derecha de la imagen
    command=buscar_productos,
    font=('Arial', 11, 'bold'),
    bg='#4CAF50', fg='white',
    activebackground='#4CAF50', activeforeground='white',
    cursor="hand2"
)
btn_buscar.grid(row=1, column=2, padx=(0, 10), pady=5, ipadx=5, ipady=5, sticky='ew')  # Ajuste de padding para el botón

btn_agregar = tk.Button(
    main_frame,
    text=" Agregar a Factura",
    image=icon_add_img,
    compound='left',
    command=agregar_a_carrito,
    font=('Arial', 11, 'bold'),
    bg='#007bff', fg='white',  # Azul más moderno
    activebackground='#007bff', activeforeground='white',
    cursor="hand2"
)
btn_agregar.grid(row=1, column=3, padx=10, pady=5, ipadx=5, ipady=5, sticky='ew')

# Área de productos buscados con scroll
tk.Label(main_frame, text="Productos Encontrados:", font=('Arial', 12, 'bold'), bg='#f0f0f0').grid(row=2, column=0,
                                                                                                   columnspan=4,
                                                                                                   pady=(15, 5),
                                                                                                   sticky='w', padx=5)

frame_container = tk.Frame(main_frame, bg='#f0f0f0', bd=1, relief='sunken')
frame_container.grid(row=3, column=0, columnspan=4, sticky='nsew', pady=5, padx=5)

canvvas = tk.Canvas(frame_container, bg='white', highlightthickness=0)
scrollbar = ttk.Scrollbar(frame_container, orient='vertical', command=canvvas.yview)
frame_productos = tk.Frame(canvvas, bg='white')  # Contenedor real de los productos

frame_productos.bind('<Configure>', lambda e: canvvas.configure(scrollregion=canvvas.bbox('all')))
canvvas.create_window((0, 0), window=frame_productos, anchor='nw')
canvvas.configure(yscrollcommand=scrollbar.set)

canvvas.pack(side='left', fill='both', expand=True)
scrollbar.pack(side='right', fill='y')

# TABLA CARRITO
tk.Label(main_frame, text="Productos en la Factura:", font=('Arial', 12, 'bold'), bg='#f0f0f0').grid(row=4, column=0,
                                                                                                     columnspan=4,
                                                                                                     pady=(15, 5),
                                                                                                     sticky='w', padx=5)

# Contenedor para el Treeview y sus botones
frame_carrito_acciones = tk.Frame(main_frame, bg='#f0f0f0')
frame_carrito_acciones.grid(row=5, column=0, columnspan=4, sticky="nsew", padx=5)

tree = ttk.Treeview(frame_carrito_acciones, columns=("codigo", "producto", "cantidad", "precio", "subtotal"),
                    show="headings", height=8)
tree.pack(side='left', fill='both', expand=True)

# Scrollbar para el carrito
scrollbar_carrito = ttk.Scrollbar(frame_carrito_acciones, orient="vertical", command=tree.yview)
scrollbar_carrito.pack(side='right', fill='y')
tree.configure(yscrollcommand=scrollbar_carrito.set)

# Configuración de columnas del Treeview
for col, ancho, ancla in zip(["codigo", "producto", "cantidad", "precio", "subtotal"], [100, 280, 80, 100, 100],
                             ['w', 'w', 'center', 'e', 'e']):
    tree.heading(col, text=col.capitalize())
    tree.column(col, width=ancho, anchor=ancla)

# Botones de acción del carrito
frame_botones_carrito = tk.Frame(main_frame, bg='#f0f0f0')
frame_botones_carrito.grid(row=6, column=0, columnspan=4, pady=5, sticky='w')

btn_eliminar = tk.Button(
    frame_botones_carrito,
    text=" Eliminar Seleccionado",
    image=icon_delete_img,
    compound='left',
    command=eliminar_del_carrito,
    font=('Arial', 10),
    bg='#dc3545', fg='white',  # Rojo para eliminar
    activebackground='#dc3545', activeforeground='white',
    cursor="hand2"
)
btn_eliminar.pack(side='left', padx=(5, 5))

btn_limpiar_carrito = tk.Button(
    frame_botones_carrito,
    text=" Limpiar Carrito",
    image=icon_clear_img,
    compound='left',
    command=limpiar_carrito_y_campos,
    font=('Arial', 10),
    bg='#ffc107', fg='black',  # Amarillo para limpiar
    activebackground='#ffc107', activeforeground='black',
    cursor="hand2"
)
btn_limpiar_carrito.pack(side='left', padx=(0, 5))

# Total de la factura
total_factura_var = tk.StringVar()
total_factura_var.set("Total: Q0.00")
lbl_total_factura = tk.Label(
    main_frame,
    textvariable=total_factura_var,
    font=('Arial', 16, 'bold'),
    bg='#f0f0f0',
    fg='#28a745'  # Verde para el total
)
lbl_total_factura.grid(row=7, column=0, columnspan=2, pady=10, sticky='w', padx=5)

# Botón Generar Factura
btn_facturar = tk.Button(
    main_frame,
    text=" Generar Factura PDF",
    image=icon_bill_img,
    compound='left',
    command=generar_factura,
    font=('Arial', 14, 'bold'),
    bg='#28a745',  # Verde Bootstrap
    fg='white',
    activebackground='#28a745', activeforeground='white',
    padx=20, pady=10,
    cursor="hand2"
)
btn_facturar.grid(row=7, column=2, columnspan=2, pady=10, sticky='e', padx=5)

# Barra de estado
status_bar = tk.Label(root, text="Listo.", bd=1, relief='sunken', anchor='w', font=('Arial', 9), bg='#e0e0e0',
                      fg='black')
status_bar.pack(side='bottom', fill='x', ipady=2)

# Configuración de redimensionamiento
main_frame.columnconfigure(1, weight=1)  # Columna del entry de búsqueda y combobox del cliente
main_frame.columnconfigure(2, weight=0)  # Los botones no crecen
main_frame.columnconfigure(3, weight=0)  # Los botones no crecen
main_frame.rowconfigure(3, weight=1)  # Fila de productos buscados
main_frame.rowconfigure(5, weight=1)  # Fila del carrito

root.mainloop()
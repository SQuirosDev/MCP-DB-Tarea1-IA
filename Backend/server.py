import asyncio
import json
import os

import mysql.connector
from mysql.connector import Error
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

# ─── Configuración ────────────────────────────────────────────────────────────

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user":os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME", "inventario"),
}

# ─── Helpers de BD ────────────────────────────────────────────────────────────

def get_connection():
    return mysql.connector.connect(**DB_CONFIG)

def serialize_row(row: dict) -> dict:
    result = {}

    for k, v in row.items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
        elif hasattr(v, "__float__"):
            result[k] = float(v)
        else:
            result[k] = v

    return result

def call_sp(sp_name: str, args: list) -> list[dict]:
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.callproc(sp_name, args)

    rows = []

    for result in cursor.stored_results():
        rows.extend(result.fetchall())

    connection.commit()
    cursor.close()
    connection.close()
    return rows

# ─── Servidor MCP ─────────────────────────────────────────────────────────────

app = Server("inventory-mcp")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="listar_productos",
            description="Lista los productos activos del inventario. Opcionalmente filtra por categoría.",
            inputSchema={
                "type": "object",
                "properties": {
                    "limite":    {"type": "integer", "description": "Máximo de productos a devolver (por defecto 50).", "default": 50},
                    "categoria": {"type": "string",  "description": "Nombre exacto de la categoría para filtrar (opcional)."},
                },
            },
        ),
        types.Tool(
            name="buscar_producto",
            description="Busca un producto por su ID exacto o por nombre (búsqueda parcial).",
            inputSchema={
                "type": "object",
                "properties": {
                    "id":     {"type": "integer", "description": "ID exacto del producto."},
                    "nombre": {"type": "string",  "description": "Texto para búsqueda parcial en el nombre."},
                },
            },
        ),
        types.Tool(
            name="agregar_producto",
            description="Agrega un nuevo producto al inventario.",
            inputSchema={
                "type": "object",
                "properties": {
                    "nombre":      {"type": "string",  "description": "Nombre del producto."},
                    "descripcion": {"type": "string",  "description": "Descripción del producto."},
                    "precio":      {"type": "number",  "description": "Precio unitario."},
                    "stock":       {"type": "integer", "description": "Cantidad inicial en stock."},
                    "categoria":   {"type": "string",  "description": "Categoría (se crea si no existe)."},
                    "sku":         {"type": "string",  "description": "Código SKU único (opcional, se genera si no se envía)."},
                },
                "required": ["nombre", "precio", "stock"],
            },
        ),
        types.Tool(
            name="actualizar_producto",
            description="Actualiza uno o varios campos de un producto existente.",
            inputSchema={
                "type": "object",
                "properties": {
                    "id":          {"type": "integer", "description": "ID del producto a actualizar."},
                    "nombre":      {"type": "string",  "description": "Nuevo nombre."},
                    "descripcion": {"type": "string",  "description": "Nueva descripción."},
                    "precio":      {"type": "number",  "description": "Nuevo precio."},
                    "stock":       {"type": "integer", "description": "Nuevo stock."},
                    "categoria":   {"type": "string",  "description": "Nueva categoría."},
                    "sku":         {"type": "string",  "description": "Nuevo SKU."},
                },
                "required": ["id"],
            },
        ),
        types.Tool(
            name="eliminar_producto",
            description="Desactiva un producto del inventario (soft-delete).",
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "ID del producto a eliminar."},
                },
                "required": ["id"],
            },
        ),
    ]

# ─── Handlers ────────────────────────────────────────────────────────────────

def handle_listar_productos(args: dict) -> str:
    rows = call_sp("SP_LISTAR_PRODUCTOS", [args.get("limite", 50), args.get("categoria", None)])

    if not rows:
        return "No se encontraron productos en el inventario."
    
    return json.dumps([serialize_row(r) for r in rows], ensure_ascii=False, indent=2)

def handle_buscar_producto(args: dict) -> str:
    prod_id = args.get("id", None)
    nombre  = args.get("nombre", None)

    if prod_id is None and nombre is None:
        return "Debes proporcionar 'id' o 'nombre' para buscar."
    
    rows = call_sp("SP_BUSCAR_PRODUCTO", [prod_id, nombre])

    if not rows:
        return "No se encontró ningún producto con los criterios indicados."
    
    return json.dumps([serialize_row(r) for r in rows], ensure_ascii=False, indent=2)

def handle_agregar_producto(args: dict) -> str:
    rows = call_sp("SP_AGREGAR_PRODUCTO", [
        args["nombre"],
        args.get("descripcion", None),
        args["precio"],
        args["stock"],
        args.get("categoria", None),
        args.get("sku", None),
    ])

    if not rows:
        return "❌ No se pudo agregar el producto."
    
    producto = serialize_row(rows[0])
    return f"✅ Producto '{producto['NOMBRE']}' agregado exitosamente con ID {producto['ID']}."

def handle_actualizar_producto(args: dict) -> str:
    prod_id = args.get("id")

    rows = call_sp("SP_ACTUALIZAR_PRODUCTO", [
        prod_id,
        args.get("nombre",      None),
        args.get("descripcion", None),
        args.get("precio",      None),
        args.get("stock",       None),
        args.get("categoria",   None),
        args.get("sku",         None),
    ])

    if not rows or rows[0].get("AFECTADOS", 0) == 0:
        return f"No se encontró un producto con ID {prod_id}."
    
    return f"✅ Producto ID {prod_id} actualizado correctamente."

def handle_eliminar_producto(args: dict) -> str:
    prod_id = args["id"]

    rows = call_sp("SP_ELIMINAR_PRODUCTO", [prod_id])

    if not rows or rows[0].get("AFECTADOS", 0) == 0:
        return f"No se encontró un producto con ID {prod_id}."
    
    return f"🗑️ Producto '{rows[0].get('NOMBRE_ELIMINADO')}' (ID {prod_id}) eliminado del inventario."

# ─── Dispatcher ──────────────────────────────────────────────────────────────

HANDLERS = {
    "listar_productos": handle_listar_productos,
    "buscar_producto": handle_buscar_producto,
    "agregar_producto": handle_agregar_producto,
    "actualizar_producto": handle_actualizar_producto,
    "eliminar_producto": handle_eliminar_producto,
}

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    handler = HANDLERS.get(name)

    if not handler:
        raise ValueError(f"Herramienta desconocida: {name}")
    
    try:
        result = handler(arguments)
    except Error as e:
        result = f"❌ Error de base de datos: {e}"
    except Exception as e:
        result = f"❌ Error inesperado: {e}"

    return [types.TextContent(type="text", text=result)]

# ─── Entry point ─────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="inventory-mcp",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())

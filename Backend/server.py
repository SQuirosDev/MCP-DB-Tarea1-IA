"""
inventory-mcp / server.py
MCP Server que expone operaciones de inventario a Claude Desktop
usando Stored Procedures de MySQL (sin SQL directo en el código).
"""

import asyncio
import json
import os
from typing import Any

import mysql.connector
from mysql.connector import Error
from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp import types

# ─── Configuración ────────────────────────────────────────────────────────────

DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER",     "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "database": os.getenv("DB_NAME",     "inventario"),
}

# ─── Helpers de BD ────────────────────────────────────────────────────────────

def get_connection() -> mysql.connector.MySQLConnection:
    return mysql.connector.connect(**DB_CONFIG)


def serialize_row(row: dict) -> dict:
    """Convierte tipos no serializables (datetime, Decimal) a tipos básicos."""
    result = {}
    for k, v in row.items():
        if hasattr(v, "isoformat"):          # datetime / date
            result[k] = v.isoformat()
        elif hasattr(v, "__float__"):         # Decimal
            result[k] = float(v)
        else:
            result[k] = v
    return result


def call_sp(sp_name: str, args: list) -> list[dict]:
    """
    Llama a un SP y devuelve los resultados como lista de dicts.
    Para SPs con OUT params, pasa los índices OUT como None en `args`.
    """
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.callproc(sp_name, args)

    rows = []
    for result in cursor.stored_results():
        rows.extend(result.fetchall())

    conn.commit()
    cursor.close()
    conn.close()
    return rows


def call_sp_with_out(sp_name: str, args: list, out_count: int) -> tuple[list[dict], list]:
    """
    Llama a un SP con parámetros OUT.
    Devuelve (filas_resultado, valores_out).
    Los parámetros OUT deben ir al final de `args` como None.
    """
    conn   = get_connection()
    cursor = conn.cursor(dictionary=True)

    result_args = cursor.callproc(sp_name, args)

    rows = []
    for result in cursor.stored_results():
        rows.extend(result.fetchall())

    # Los OUT params están al final de result_args
    out_values = list(result_args[-out_count:])

    conn.commit()
    cursor.close()
    conn.close()
    return rows, out_values


# ─── Servidor MCP ─────────────────────────────────────────────────────────────

app = Server("inventory-mcp")


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="listar_productos",
            description=(
                "Lista los productos activos del inventario. "
                "Opcionalmente filtra por categoría y limita el número de resultados."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "limite": {
                        "type": "integer",
                        "description": "Máximo de productos a devolver (por defecto 50).",
                        "default": 50,
                    },
                    "categoria": {
                        "type": "string",
                        "description": "Nombre exacto de la categoría para filtrar (opcional).",
                    },
                },
            },
        ),
        types.Tool(
            name="buscar_producto",
            description=(
                "Busca un producto por su ID exacto o por nombre (búsqueda parcial). "
                "Proporciona solo uno de los dos parámetros."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "id": {
                        "type": "integer",
                        "description": "ID exacto del producto.",
                    },
                    "nombre": {
                        "type": "string",
                        "description": "Texto para búsqueda parcial en el nombre.",
                    },
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
                    "categoria":   {"type": "string",  "description": "Categoría (se crea automáticamente si no existe)."},
                    "sku":         {"type": "string",  "description": "Código SKU único."},
                },
                "required": ["nombre", "precio", "stock"],
            },
        ),
        types.Tool(
            name="actualizar_producto",
            description=(
                "Actualiza uno o varios campos de un producto existente. "
                "Solo envía los campos que quieres cambiar."
            ),
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
            description=(
                "Desactiva un producto del inventario (soft-delete). "
                "El producto deja de aparecer en listados pero se conserva en la BD."
            ),
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
    limite    = args.get("limite", 50)
    categoria = args.get("categoria", None)

    rows = call_sp("sp_listar_productos", [limite, categoria])

    if not rows:
        return "No se encontraron productos en el inventario."

    rows = [serialize_row(r) for r in rows]
    return json.dumps(rows, ensure_ascii=False, indent=2)


def handle_buscar_producto(args: dict) -> str:
    prod_id = args.get("id", None)
    nombre  = args.get("nombre", None)

    if prod_id is None and nombre is None:
        return "Debes proporcionar 'id' o 'nombre' para buscar."

    rows = call_sp("sp_buscar_producto", [prod_id, nombre])

    if not rows:
        return "No se encontró ningún producto con los criterios indicados."

    rows = [serialize_row(r) for r in rows]
    return json.dumps(rows, ensure_ascii=False, indent=2)


def handle_agregar_producto(args: dict) -> str:
    sp_args = [
        args["nombre"],
        args.get("descripcion", None),
        args["precio"],
        args["stock"],
        args.get("categoria", None),
        args.get("sku", None),
        None,  # OUT p_nuevo_id
    ]

    _, out_vals = call_sp_with_out("sp_agregar_producto", sp_args, out_count=1)
    nuevo_id = out_vals[0]

    return f"✅ Producto '{args['nombre']}' agregado exitosamente con ID {nuevo_id}."


def handle_actualizar_producto(args: dict) -> str:
    prod_id = args.get("id")
    sp_args = [
        prod_id,
        args.get("nombre",      None),
        args.get("descripcion", None),
        args.get("precio",      None),
        args.get("stock",       None),
        args.get("categoria",   None),
        args.get("sku",         None),
        None,  # OUT p_afectados
    ]

    _, out_vals = call_sp_with_out("sp_actualizar_producto", sp_args, out_count=1)
    afectados = out_vals[0]

    if not afectados:
        return f"No se encontró un producto con ID {prod_id}."

    return f"✅ Producto ID {prod_id} actualizado correctamente."


def handle_eliminar_producto(args: dict) -> str:
    prod_id = args["id"]
    sp_args = [prod_id, None, None]  # OUT: nombre, afectados

    _, out_vals = call_sp_with_out("sp_eliminar_producto", sp_args, out_count=2)
    nombre_eliminado, afectados = out_vals

    if not afectados:
        return f"No se encontró un producto con ID {prod_id}."

    return f"🗑️ Producto '{nombre_eliminado}' (ID {prod_id}) eliminado del inventario."


# ─── Dispatcher ──────────────────────────────────────────────────────────────

HANDLERS = {
    "listar_productos":    handle_listar_productos,
    "buscar_producto":     handle_buscar_producto,
    "agregar_producto":    handle_agregar_producto,
    "actualizar_producto": handle_actualizar_producto,
    "eliminar_producto":   handle_eliminar_producto,
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
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())

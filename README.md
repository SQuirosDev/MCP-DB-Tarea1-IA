# 🗃️ Inventory MCP — MySQL · Stored Procedures · Python (uv)

MCP Server en Python que conecta Claude Desktop con un inventario MySQL,
usando exclusivamente **Stored Procedures** como capa de acceso a datos.

---

## 📁 Estructura del proyecto

```
inventory-mcp/
├── sql/
│   ├── 01_tablas.sql             # Schema y tablas
│   └── 02_stored_procedures.sql  # Todos los SPs
├── server.py                     # MCP Server (llama SPs, nunca SQL directo)
├── pyproject.toml                # Configuración del proyecto (uv)
├── .env.example                  # Variables de entorno
└── README.md
```

---

## ⚙️ Instalación con `uv`

### 1. Instalar uv (si no lo tienes)

```bash
# macOS / Linux
curl -Lsf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 2. Crear el entorno virtual e instalar dependencias

```bash
cd inventory-mcp

# Crea el venv en .venv/ e instala todo lo de pyproject.toml
uv sync
```

Esto genera automáticamente el `uv.lock` y el venv en `.venv/`.

### 3. Verificar que funciona

```bash
uv run python server.py
```

---

## 🗄️ Configurar la base de datos MySQL

### Paso 1 — Crear tablas

```bash
mysql -u root -p < sql/01_tablas.sql
```

### Paso 2 — Crear Stored Procedures

```bash
mysql -u root -p < sql/02_stored_procedures.sql
```

### Paso 3 — Variables de entorno

```bash
cp .env.example .env
# Edita .env con tus credenciales reales
```

---

## 🔌 Conectar con Claude Desktop

> **Clave:** Claude Desktop necesita la ruta **absoluta** al ejecutable de Python
> dentro del venv, no el comando `uv run`. Esto asegura que use exactamente
> las dependencias instaladas y evita cualquier problema con el PATH.

Edita el archivo de configuración de Claude Desktop:

| OS | Ruta |
|---|---|
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

### macOS / Linux

```json
{
  "mcpServers": {
    "inventory-mcp": {
      "command": "/RUTA/ABSOLUTA/inventory-mcp/.venv/bin/python",
      "args": ["/RUTA/ABSOLUTA/inventory-mcp/server.py"],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
        "DB_USER": "root",
        "DB_PASSWORD": "tu_password_aqui",
        "DB_NAME": "inventario"
      }
    }
  }
}
```

### Windows

```json
{
  "mcpServers": {
    "inventory-mcp": {
      "command": "C:\\RUTA\\inventory-mcp\\.venv\\Scripts\\python.exe",
      "args": ["C:\\RUTA\\inventory-mcp\\server.py"],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "3306",
        "DB_USER": "root",
        "DB_PASSWORD": "tu_password_aqui",
        "DB_NAME": "inventario"
      }
    }
  }
}
```

> Cómo encontrar la ruta exacta del Python en tu venv:
> ```bash
> # macOS/Linux
> uv run which python
>
> # Windows
> uv run where python
> ```

Reinicia Claude Desktop después de editar el archivo.

---

## 🛠️ Stored Procedures disponibles

| SP | Descripción |
|---|---|
| `sp_listar_productos` | Lista productos activos, filtrable por categoría |
| `sp_buscar_producto` | Busca por ID exacto o nombre parcial |
| `sp_agregar_producto` | Inserta un nuevo producto (crea la categoría si no existe) |
| `sp_actualizar_producto` | Actualiza solo los campos enviados (IFNULL pattern) |
| `sp_eliminar_producto` | Soft-delete: marca `activo = 0` sin borrar el registro |

---

## 💬 Ejemplos de uso en Claude Desktop

```
"Lista todos los productos de la categoría Electrónica"
"Agrega un producto: Laptop Dell XPS, precio 1200, stock 10, categoría Electrónica"
"Actualiza el stock del producto ID 3 a 50 unidades"
"Busca productos que contengan 'silla' en el nombre"
"Elimina el producto con ID 7"
```

---

## 🏗️ Arquitectura por capas

```
Claude Desktop
     │  (MCP Protocol)
     ▼
  server.py          ← Capa MCP: define tools, valida parámetros
     │  (callproc)
     ▼
Stored Procedures    ← Capa de datos: toda la lógica SQL aquí
     │
     ▼
  MySQL DB           ← Tablas: productos, categorias
```

El servidor Python **nunca escribe SQL directamente**. Toda interacción
con la BD pasa por los SPs, lo que facilita cambiar la lógica de negocio
sin tocar el código Python.

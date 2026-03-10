# Inventory MCP — MySQL · Stored Procedures · Python (uv)

MCP Server en Python que conecta Claude Desktop con un inventario MySQL,
usando exclusivamente **Stored Procedures** como capa de acceso a datos.

---

## Estructura del proyecto

```
MCP-DB-Tarea1-IA/
├── Backend/
│   └── server.py
├── Database/
│   ├── 01_tablas.sql
│   └── 02_stored_procedures.sql
├── Docs/
│   └── Tarea y prueba corta 2.docx
├── .env
├── .gitignore
├── .python-version
├── LICENSE
├── pyproject.toml
├── README.md
└── uv.lock
```

---

## Instalación con `uv`

### 1. Instalar uv (si no lo tienes)

```bash
# Windows (PowerShell)
pip install uv
```

### 2. Crear el entorno virtual e instalar dependencias

```bash
cd MCP-DB-Tarea1-IA
uv sync
```

Esto genera automáticamente el `uv.lock` y el venv en `.venv/`.

### 3. Verificar que funciona

```bash
uv run python server.py
```

---

## Configurar la base de datos MySQL

### Paso 1 — Crear tablas

* Ejecutar el script en MySQL

### Paso 2 — Crear Stored Procedures

* Ejecutar el script en MySQL


### Paso 3 — Variables de entorno

> Nota: Crear el documento `.env` en la carpeta `MCP-DB-Tarea1-IA/`

```bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=tu_password_aqui
DB_NAME=INVENTARIO_DB
```

---

## Conectar con Claude Desktop

> **Clave:** Claude Desktop necesita la ruta **absoluta** al ejecutable de Python
> dentro del venv, no el comando `uv run where python`. Esto asegura que use exactamente
> las dependencias instaladas y evita cualquier problema con el PATH.

Edita el archivo de configuración de Claude Desktop:

| OS | Ruta |
|---|---|
| Windows | `C:\\Users\\...\\TareaQuiz2\\MCP-DB-Tarea1-IA\\.venv\\Scripts\\python.exe` |

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
        "DB_NAME": "INVENTARIO_DB"
      }
    }
  }
}
```

Reinicia Claude Desktop con `ps "Claude" | kill` después de editar el archivo.

---

## Stored Procedures disponibles

| SP | Descripción |
|---|---|
| `SP_AGREGAR_PRODUCTO` | Inserta un nuevo producto (crea la categoría si no existe) |
| `SP_LISTAR_PRODUCTOS` | Lista productos activos, filtrable por categoría |
| `SP_BUSCAR_PRODUCTO` | Busca por ID exacto o nombre parcial |
| `SP_ACTUALIZAR_PRODUCTO` | Actualiza solo los campos enviados (IFNULL pattern) |
| `SP_ELIMINAR_PRODUCTO` | Soft-delete: marca `activo = 0` sin borrar el registro |

---

## Ejemplos de uso en Claude Desktop

* "Lista todos los productos de la categoría Electrónica"
* "Agrega un producto: Laptop Dell XPS, precio 1200, stock 10, categoría Electrónica"
* "Actualiza el stock del producto ID 3 a 50 unidades"
* "Busca productos que contengan 'silla' en el nombre"
* "Elimina el producto con ID 7"


---

## Arquitectura por capas

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

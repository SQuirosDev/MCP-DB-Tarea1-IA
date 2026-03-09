-- ============================================================
-- 02_stored_procedures.sql
-- Todos los SPs que usa el MCP Server
-- Ejecutar después de 01_tablas.sql
-- ============================================================

USE inventario;

-- ──────────────────────────────────────────────────────────
-- SP: sp_listar_productos
-- Parámetros:
--   p_limite      INT           — max filas (default 50)
--   p_categoria   VARCHAR(100)  — filtro opcional (NULL = todos)
-- ──────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_listar_productos;
DELIMITER $$
CREATE PROCEDURE sp_listar_productos(
    IN p_limite    INT,
    IN p_categoria VARCHAR(100)
)
BEGIN
    SET p_limite = IFNULL(p_limite, 50);

    IF p_categoria IS NOT NULL THEN
        SELECT
            p.id, p.nombre, p.descripcion, p.precio,
            p.stock, c.nombre AS categoria, p.sku,
            p.activo, p.creado_en, p.actualizado_en
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE c.nombre = p_categoria
          AND p.activo = 1
        ORDER BY p.nombre
        LIMIT p_limite;
    ELSE
        SELECT
            p.id, p.nombre, p.descripcion, p.precio,
            p.stock, c.nombre AS categoria, p.sku,
            p.activo, p.creado_en, p.actualizado_en
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.activo = 1
        ORDER BY p.nombre
        LIMIT p_limite;
    END IF;
END$$
DELIMITER ;


-- ──────────────────────────────────────────────────────────
-- SP: sp_buscar_producto
-- Parámetros:
--   p_id     INT          — búsqueda por ID exacto (opcional)
--   p_nombre VARCHAR(255) — búsqueda parcial por nombre (opcional)
-- ──────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_buscar_producto;
DELIMITER $$
CREATE PROCEDURE sp_buscar_producto(
    IN p_id     INT,
    IN p_nombre VARCHAR(255)
)
BEGIN
    IF p_id IS NOT NULL THEN
        SELECT
            p.id, p.nombre, p.descripcion, p.precio,
            p.stock, c.nombre AS categoria, p.sku,
            p.activo, p.creado_en, p.actualizado_en
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.id = p_id;
    ELSE
        SELECT
            p.id, p.nombre, p.descripcion, p.precio,
            p.stock, c.nombre AS categoria, p.sku,
            p.activo, p.creado_en, p.actualizado_en
        FROM productos p
        LEFT JOIN categorias c ON p.categoria_id = c.id
        WHERE p.nombre LIKE CONCAT('%', p_nombre, '%')
        ORDER BY p.nombre;
    END IF;
END$$
DELIMITER ;


-- ──────────────────────────────────────────────────────────
-- SP: sp_agregar_producto
-- Parámetros:
--   p_nombre      VARCHAR(255)
--   p_descripcion TEXT
--   p_precio      DECIMAL(10,2)
--   p_stock       INT
--   p_categoria   VARCHAR(100)  — nombre de categoría (se crea si no existe)
--   p_sku         VARCHAR(100)
-- Salida: nuevo ID en @out_id
-- ──────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_agregar_producto;
DELIMITER $$
CREATE PROCEDURE sp_agregar_producto(
    IN  p_nombre      VARCHAR(255),
    IN  p_descripcion TEXT,
    IN  p_precio      DECIMAL(10, 2),
    IN  p_stock       INT,
    IN  p_categoria   VARCHAR(100),
    IN  p_sku         VARCHAR(100),
    OUT p_nuevo_id    INT
)
BEGIN
    DECLARE v_cat_id INT DEFAULT NULL;

    -- Resolver o crear categoría
    IF p_categoria IS NOT NULL AND p_categoria != '' THEN
        SELECT id INTO v_cat_id
        FROM categorias
        WHERE nombre = p_categoria
        LIMIT 1;

        IF v_cat_id IS NULL THEN
            INSERT INTO categorias (nombre) VALUES (p_categoria);
            SET v_cat_id = LAST_INSERT_ID();
        END IF;
    END IF;

    INSERT INTO productos (nombre, descripcion, precio, stock, categoria_id, sku)
    VALUES (p_nombre, p_descripcion, p_precio, p_stock, v_cat_id, p_sku);

    SET p_nuevo_id = LAST_INSERT_ID();
END$$
DELIMITER ;


-- ──────────────────────────────────────────────────────────
-- SP: sp_actualizar_producto
-- Parámetros (todos opcionales excepto p_id):
--   p_id, p_nombre, p_descripcion, p_precio,
--   p_stock, p_categoria, p_sku
-- Salida: filas afectadas en @out_afectados
-- ──────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_actualizar_producto;
DELIMITER $$
CREATE PROCEDURE sp_actualizar_producto(
    IN  p_id          INT,
    IN  p_nombre      VARCHAR(255),
    IN  p_descripcion TEXT,
    IN  p_precio      DECIMAL(10, 2),
    IN  p_stock       INT,
    IN  p_categoria   VARCHAR(100),
    IN  p_sku         VARCHAR(100),
    OUT p_afectados   INT
)
BEGIN
    DECLARE v_cat_id INT DEFAULT NULL;

    -- Resolver o crear categoría si se envía
    IF p_categoria IS NOT NULL AND p_categoria != '' THEN
        SELECT id INTO v_cat_id
        FROM categorias
        WHERE nombre = p_categoria
        LIMIT 1;

        IF v_cat_id IS NULL THEN
            INSERT INTO categorias (nombre) VALUES (p_categoria);
            SET v_cat_id = LAST_INSERT_ID();
        END IF;
    END IF;

    UPDATE productos
    SET
        nombre        = IFNULL(p_nombre,      nombre),
        descripcion   = IFNULL(p_descripcion, descripcion),
        precio        = IFNULL(p_precio,      precio),
        stock         = IFNULL(p_stock,       stock),
        categoria_id  = CASE
                            WHEN p_categoria IS NOT NULL THEN v_cat_id
                            ELSE categoria_id
                        END,
        sku           = IFNULL(p_sku,         sku)
    WHERE id = p_id;

    SET p_afectados = ROW_COUNT();
END$$
DELIMITER ;


-- ──────────────────────────────────────────────────────────
-- SP: sp_eliminar_producto
-- Hace soft-delete (activo = 0) para conservar historial
-- Parámetros: p_id INT
-- Salida: nombre del producto en p_nombre_eliminado
-- ──────────────────────────────────────────────────────────
DROP PROCEDURE IF EXISTS sp_eliminar_producto;
DELIMITER $$
CREATE PROCEDURE sp_eliminar_producto(
    IN  p_id              INT,
    OUT p_nombre_eliminado VARCHAR(255),
    OUT p_afectados        INT
)
BEGIN
    SELECT nombre INTO p_nombre_eliminado
    FROM productos
    WHERE id = p_id
    LIMIT 1;

    IF p_nombre_eliminado IS NOT NULL THEN
        UPDATE productos SET activo = 0 WHERE id = p_id;
        SET p_afectados = ROW_COUNT();
    ELSE
        SET p_afectados = 0;
    END IF;
END$$
DELIMITER ;

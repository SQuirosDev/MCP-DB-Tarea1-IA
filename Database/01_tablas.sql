-- ============================================================
-- 01_tablas.sql
-- Crea el schema y la tabla principal de inventario
-- ============================================================

CREATE DATABASE IF NOT EXISTS inventario
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE inventario;

CREATE TABLE IF NOT EXISTS categorias (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    nombre      VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    creado_en   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS productos (
    id             INT AUTO_INCREMENT PRIMARY KEY,
    nombre         VARCHAR(255)   NOT NULL,
    descripcion    TEXT,
    precio         DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    stock          INT            NOT NULL DEFAULT 0,
    categoria_id   INT,
    sku            VARCHAR(100)   UNIQUE,
    activo         TINYINT(1)     NOT NULL DEFAULT 1,
    creado_en      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    CONSTRAINT fk_categoria
        FOREIGN KEY (categoria_id)
        REFERENCES categorias (id)
        ON DELETE SET NULL
);

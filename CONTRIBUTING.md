# Convenciones del proyecto

Código y nombres en inglés; documentación y entregables en español. Configuración centralizada en TOML, rutas relativas mediante pathlib y lógica reutilizable en src/beyond_beta.

Los documentos finales se maquetan en LaTeX y se compilan con MiKTeX/XeLaTeX. La plantilla está en templates/latex y las fuentes generadas permanecen junto a sus PDF. Los datos, tablas, resultados y fuentes bibliográficas deben poder rastrearse hasta una ejecución comprobada.

Los tests usan datos sintéticos identificados y no requieren Internet. Las fuentes originales se conservan intactas con hashes y procedencia. No se añaden datos brutos o documentos docentes al seguimiento sin revisar sus permisos.

Los cambios metodológicos deben quedar registrados en docs/decisions.md. Los informes distinguen resultados, limitaciones y decisiones pendientes. La publicación y la licencia requieren aprobación del propietario.

# Registro de decisiones

## Requisitos comprobados en el enunciado

Informe DOC o PDF; cálculos Excel o Python; al menos 61 precios ajustados mensuales; CAPM con alfa, beta y significancia; SML virtual; cartera con pesos no nulos y suma uno; FF3 e interpretación de alfa y exposiciones. El enunciado habla de cuatro activos.

## Diseño adoptado

1. Desarrollar el análisis y sus entregables, manteniendo el proyecto privado hasta revisar su publicación.
2. Regresiones en USD con la copia de factores del profesor y descriptivos adicionales en EUR.
3. Incorporar EUNH.DE e IUSQ.DE, con identidad verificada y 61 cierres válidos en la muestra.
4. Cartera con seis activos y pesos 1/6, rebalanceada mensualmente.
5. Conservar la versión de factores del profesor, conservada localmente. La cabecera indica CRSP 202609; el SHA256 se fija en la configuración.

## Aprobación del universo de seis activos

El profesor ha confirmado que el trabajo puede utilizar seis activos. La ampliación queda aprobada; se mantiene la referencia al requisito original de cuatro activos.

## Decisiones de implementación

Ventana fija septiembre 2021-septiembre 2026 de precios y octubre 2021-septiembre 2026 de rentabilidades. Adj Close, con auto_adjust=False. No se rellena un mes ausente. Para convertir cada activo se usa EUR/USD de la misma fecha o anterior, antigüedad máxima de cuatro días naturales. No hay interpolación ni uso de un cambio posterior.

OLS convencional como principal, pues el enunciado no especifica inferencia alternativa. HAC con corrección de muestra, distribución t y retardos floor(4*(T/100)^(2/9)); para T=60 son tres retardos. Significancia nominal del 5 %, sin corrección por comparaciones múltiples; se documenta esa limitación.

Sin optimización, costes, impuestos ni posiciones cortas. Los costes internos de los productos quedan reflejados en los precios en la medida en que los incorpora la fuente. El informe y la metodología se maquetan en LaTeX y se compilan a PDF con MiKTeX. El enunciado admite PDF y no exige Word.

## Opciones y pendientes

La alternativa de un análisis principal en EUR se explica en metodología; no se ejecuta con los factores USD sin adaptar su definición. Licencia y publicación requieren elección del propietario. No se ha encontrado una autorización inequívoca para redistribuir el CSV de factores: se conserva localmente, con atribución y fuera de Git.

## Criterios de implementación

- Se restringe el diseño a pesos estrictamente positivos, moneda de análisis USD, activos cotizados en EUR/USD y entre dos y diez activos. Las alternativas de pesos y ventana se permiten con recuentos coherentes; las muestras inferiores a sesenta rentabilidades se identifican como insuficientes para la entrega de cinco años.
- Las opciones de inferencia y cartera admiten únicamente OLS principal, regla HAC fija segura, rebalanceo mensual y costes/impuestos cero. Las alternativas se rechazan expresamente; no se amplía el alcance con un motor fiscal o de costes.
- Se incorpora tolerancia aproximada de frescura del cierre mensual, siete días naturales por defecto, separada de la tolerancia FX. No equivale a un calendario bursátil exacto.
- La raíz del proyecto se descubre desde el directorio de ejecución o se indica explícitamente. La ubicación del TOML no cambia las rutas de datos. Se verifica la ruta y el hash de la configuración usada en el análisis.
- La trazabilidad se divide en análisis y documentos, con inventarios explícitos, identificador de ejecución y estado incompleto durante las escrituras. La generación de documentos no sobrescribe fuentes manuales de docs.
- Las versiones de dependencias no se actualizan en esta revisión. La CI básica no compila PDF y ejecuta solo datos sintéticos con bloqueo de red.

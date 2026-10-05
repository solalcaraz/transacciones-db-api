# Detector de anomalías en transacciones bancarias

API y panel web que analizan las transacciones de una red de cajeros automáticos y marcan a los clientes con comportamiento sospechoso, usando tres modelos de detección de anomalías. Es el trabajo práctico (TP) de la materia Base de Datos de la Tecnicatura en Programación Informática (UNSAM, 2025), que hicimos en un equipo de seis personas. Este repositorio es el backend; el front está en [frontend-transacciones](https://github.com/solalcaraz/frontend-transacciones).

## Problema que resuelve

La consigna pedía diseñar una base de datos de transacciones financieras y aplicar técnicas de IA para detectar posibles fraudes. El dataset que usamos, [Wisabi Bank](https://www.kaggle.com/datasets/obinnaiheanachor/wisabi-bank-dataset) de Kaggle, tiene transacciones de cajeros de cinco estados de Nigeria, pero no indica cuáles son fraude. Sin etiquetas no hay contra qué entrenar ni contra qué medir, así que el problema no se puede plantear como una clasificación: hay que encontrar lo que se aparta del comportamiento habitual y, además, poder explicarle a quien mira el reporte por qué se marcó a alguien.

El otro desafío fue el volumen: los CSV originales pesan 160 MB y los modelos se entrenan en el momento de cada consulta, sin resultados guardados.

## Demo

![Recorrido por el dashboard, el reporte de clientes sospechosos, el detalle de un cliente y las tablas de transacciones y clientes](docs/demo.gif)

El recorrido pasa por el dashboard con el gráfico de clientes, el reporte de sospechosos, el detalle de un cliente con dos transacciones marcadas y las tablas de transacciones y clientes. Las esperas de carga están aceleradas en el GIF: con los datos completos, el dashboard tarda unos 9 segundos en mostrarse porque los modelos se entrenan de nuevo en cada pedido.

## Tecnologías

- **Backend:** Python, FastAPI, SQLAlchemy y SQLite.
- **Detección:** scikit-learn (Isolation Forest, Local Outlier Factor y K-Means), pandas y NumPy.
- **Gráficos:** Plotly.
- **Front:** HTML, JavaScript sin frameworks y Bootstrap 5 ([repositorio aparte](https://github.com/solalcaraz/frontend-transacciones)).

## Cómo funciona

`procesar_datos.py` toma los CSV originales de `data_original/`, se queda con enero de 2022 y adapta las columnas al modelo de la base. El resultado queda en `data/`: 173.242 transacciones de 8.819 clientes en 50 cajeros. `cargar_csvs.py` crea las tablas en SQLite y carga esos archivos. La API expone el CRUD de clientes, cajeros, transacciones y tipos de transacción, y los endpoints de análisis que usa el front:

| Endpoint | Qué devuelve |
|---|---|
| `GET /anomalias/clientes_sospechosos` | Los clientes marcados y los motivos de cada uno |
| `GET /anomalias/transacciones_por_cliente/{id}` | Todas las transacciones del cliente, con las sospechosas marcadas y su score |
| `GET /estadisticas` | Totales y porcentaje de clientes sospechosos para el dashboard |
| `GET /anomalias/graficos/clientes_sospechosos` | El gráfico de dispersión de clientes, como HTML de Plotly |

La detección está en `deteccion.py` y trabaja en dos niveles:

- **Clientes.** Para cada cliente calcula seis indicadores: cantidad de transacciones, monto promedio, desvío, máximo, mínimo y tiempo promedio entre transacciones. Isolation Forest, LOF y K-Means analizan esos indicadores por separado, y un cliente queda como sospechoso si al menos dos de los tres lo marcan.
- **Transacciones de un cliente.** Cuando se abre el detalle de un cliente, los mismos tres modelos analizan sus transacciones comparándolas solo con su propio historial: monto, hora, si fue de noche o en fin de semana, y segundos desde la transacción anterior. Una transacción queda marcada si la detectan al menos dos modelos y el score combinado llega a 50 sobre 100.

Entre todos buscamos y limpiamos el dataset, diseñamos el modelo de datos (entidades, relaciones, restricciones y alcance de la base), creamos la base en SQLite según el diagrama entidad-relación y cargamos los datos procesados.

Las decisiones de diseño también las tomamos en equipo. Usamos tres modelos porque cada uno mira algo distinto: Isolation Forest aísla los puntos raros respecto de todo el conjunto, LOF compara cada punto con la densidad de sus vecinos y K-Means mide qué tan lejos queda del grupo al que pertenece. Pedir que coincidan dos evita depender de las rarezas de uno solo.

Como los modelos no explican por qué marcan a alguien, cada cliente sospechoso trae además motivos legibles, como "monto muy alto comparado con su promedio" o "transacciones demasiado seguidas". El reporte arranca por los clientes y recién en el detalle analiza transacciones, porque era más eficiente que analizarlas todas juntas: sobre las 173.242 transacciones, los modelos tardan unos 13 segundos y marcan 13.233. Por el mismo motivo nos quedamos con un solo mes de datos.

Las decisiones que tomé y por qué:

- **Separar los modelos en `deteccion.py`.** La lógica de machine learning estaba mezclada con los endpoints y el cálculo de indicadores y de motivos estaba duplicado. Ahora son funciones que reciben un DataFrame y no dependen de FastAPI ni de la base, y los endpoints solo consultan y arman la respuesta.
- **Mostrar errores en lugar de datos de ejemplo.** Cuando la API no respondía, el front mostraba clientes y cajeros inventados que podían confundirse con datos reales.

## Cómo correrlo

Se necesita Python 3.11 o superior. Los datos ya vienen procesados en `data/`; solo hay que instalar las dependencias, cargar la base y levantar la API:

```bash
pip install -r requerimientos.txt
python cargar_csvs.py
uvicorn main:app --reload
```

La ruta de la base y los orígenes que acepta la API se pueden cambiar con las variables de entorno `DATABASE_URL` y `ORIGENES_PERMITIDOS`.

Para ver el panel, levantá el [front](https://github.com/solalcaraz/frontend-transacciones) con `python -m http.server 5500` y abrí http://127.0.0.1:5500.

## Qué aprendí y qué mejoraría

**Qué aprendí**

- A trabajar con detección de anomalías cuando no hay etiquetas: sin un "resultado correcto" contra el cual medir, la forma de darle confianza al resultado es combinar modelos y acompañar cada alerta con un motivo que se pueda leer.
- Que un modelo con parámetros fijos puede romperse cuando se aplica a conjuntos chicos. K-Means usaba siempre 5 grupos, y el detalle de los clientes con menos de 5 transacciones devolvía un error 500.
- A refactorizar sin tests: guardé las respuestas de todos los endpoints antes de tocar el código y las usé como referencia para comparar después de cada cambio.

**Qué mejoraría**

- **Revisar el umbral del score por transacción.** En los tres modelos, un score más bajo significa "más anómalo", pero el filtro pide un score combinado de 50 o más. En la práctica, solo 41 de los 351 clientes sospechosos tienen alguna transacción marcada en su detalle, y las marcadas aparecen al final de la lista. Lo dejé como estaba porque corregirlo cambia los resultados del TP.
- **Entrenar una vez y guardar los resultados.** Hoy cada pedido vuelve a entrenar los modelos: las estadísticas y el gráfico del dashboard tardan más de 4 segundos cada uno, y el reporte de clientes otro tanto.
- **Agregar tests automáticos** que reemplacen la comparación manual de respuestas.

## Autoría y mejoras

Este repositorio es un fork de **[IlledNacu/transacciones-db-api](https://github.com/IlledNacu/transacciones-db-api)**, el trabajo práctico que hicimos en equipo entre septiembre y noviembre de 2025. El tag [`tp-original-2025`](https://github.com/solalcaraz/transacciones-db-api/tree/tp-original-2025) marca el TP tal como lo entregamos. El front tiene su propio fork, [solalcaraz/frontend-transacciones](https://github.com/solalcaraz/frontend-transacciones), de [IlledNacu/frontend-transacciones](https://github.com/IlledNacu/frontend-transacciones).

**Equipo:** María Sol Alcaraz, Illed Nacucchio, Damián Palomba, Lorenzo Graizzaro, Luis Mazo y Santiago Rodríguez Spina.

**Mi parte en la versión original**:

- Participé en la definición de la idea del proyecto y en la limpieza del dataset.
- Armé consultas de la API (endpoints) junto con otros dos compañeros.
- Hice el gráfico de dispersión de clientes sospechosos del dashboard: ubica a cada cliente según su monto promedio y el tiempo entre sus transacciones, y usa Isolation Forest para resaltar a los que se salen de lo común.
- Hice las pantallas paginadas de clientes y de cajeros, y la de tipos de transacción.
- Hice las correcciones finales para que se mostraran todas las transacciones y todos los clientes: las listas quedaban cortadas y no se veía el total.

**Lo que hice después en este fork**:

- Corregí los errores que encontré al correr el proyecto:
  - `requerimientos.txt` tenía las dependencias en una sola línea y `pip install -r` fallaba.
  - El detalle de un cliente devolvía error 500 si tenía menos de 5 transacciones (17 de los 351 sospechosos) o una sola.
  - `procesar_datos.py` se cortaba en consolas de Windows por los emojis de sus mensajes.
  - Al borrar un tipo de transacción, la API respondía "Número de cuenta eliminado"; ahora dice "Tipo de transacción eliminado".
  - En el front, si fallaban las estadísticas, el dashboard tampoco cargaba el gráfico, y cuando la API no respondía se mostraban datos de ejemplo inventados.
- Separé la detección de anomalías en `deteccion.py` y dejé los endpoints solo con la consulta y la respuesta.
- En el front, junté el código que estaba copiado en cada página en `comun.js`, `tabla.js` y `menu.js`.
- Saqué la configuración del código: la ruta de la base y los orígenes permitidos por CORS se leen de variables de entorno, y la URL de la API en el front está en `config.js`.
- Eliminé el código comentado, los imports sin uso, los comentarios que solo repetían el código y dos archivos que ya no se usaban: una versión anterior de la detección y un script que leía un CSV inexistente.
- Grabé la demo y reescribí este README.

Para comprobar que el comportamiento no cambió, guardé las respuestas de todos los endpoints con el código original, incluido el detalle de cada uno de los 351 clientes sospechosos, y las comparé con las del código nuevo: son idénticas, salvo en los errores corregidos. En el front recorrí cada página con Playwright antes y después (carga, búsqueda, paginación, detalle, altas y edición) y comparé el texto que se ve en pantalla.

# Transmetro (Ciudad de Guatemala) – borrador GTFS no oficial

Feed GTFS estático **no oficial** construido a partir del mapa público de la Municipalidad de Guatemala
(paradas) y las páginas de cada línea (horarios de servicio). Generado con `python build.py`.

## Frecuencias estimadas

**Las frecuencias (`frequencies.txt`) son estimadas, no oficiales.** La Municipalidad no las publica.
Valores usados: días hábiles 5 min en horas pico (06:00–09:00 y 17:00–20:00) y 10 min el resto del día;
sábados 10 min; domingos 15 min. Los tiempos de recorrido se calculan a 18 km/h + 20 s por parada.
Con los datos de operación de la Municipalidad se reemplazan directamente.

El orden de las paradas y los sentidos se tomaron de los diagramas "Estaciones de Línea N" de muniguate.com
(consultados el 2026-10-16); todas las líneas son circuitos (L1, L2, L6, L7, L12, L12E, L13, L18 y L18R). Los horarios de servicio son los de cada página de línea.

Líneas incluidas: 1, 2, 6, 7, 12, 13 y 18 (la L18 y el circuito San Rafael–Paraíso son dos circuitos que se conectan en Atlántida, estación de transbordo). Las coordenadas de las estaciones
provienen de los mapas de Google My Maps de la Municipalidad.
`shapes.txt` se genera ajustando la secuencia de paradas de cada viaje al trazado oficial de cada línea (KML de Google My Maps
en `reference/Transmetro/`, ver `shapes_lib.py`). La L12 y su expreso (Centra Sur / Trébol / Plaza El Amate) son circuitos: ida hasta Plaza El Amate y regreso por el mismo corredor (descripción del operador).
TuBus tiene su propio feed (ver abajo).

## Datos cifrados

Por ahora los datos y el código que los genera (`build.py`, `shapes_lib.py`, `gtfs/`, el zip, los KML) **no** se publican en claro:
se guardan cifrados (AES-256) en `data.tar.gz.gpg`. `./protect.sh` cifra y `./unprotect.sh` descifra, usando la frase de
contraseña del archivo `~/.gtfs-rt-passphrase` (fuera del repositorio).

## Simulación en tiempo real (GTFS-RT)

`simulate.py` (L7 sentido La Merced) mueve buses falsos por el `shape` con la frecuencia estimada y genera `VehiclePositions` y
`TripUpdates` válidos (`--once`, `--live` cada 10 s, `--replay` para el mapa). Prueba el pipeline, no la exactitud de los datos.
`docs/` es el mapa para GitHub Pages (reproduce 30 min de feed simulado; muestra los buses y "próximo bus en N min").
Requiere `pip install -r requirements.txt`.

## Planificador de viajes (a pie + bus)

`otp/run.sh` levanta [OpenTripPlanner](https://www.opentripplanner.org/) 2.6 en local con este GTFS y el mapa de OpenStreetMap de
Guatemala (© colaboradores de OpenStreetMap, ODbL); caminar y los trasbordos entre líneas los resuelve OTP. El mapa de `docs/`
tiene un panel "Planificar viaje": se elige origen y destino sobre el mapa y se consulta `http://localhost:8080/otp/gtfs/v1`
(otro servidor con `?otp=URL`). En GitHub Pages el panel solo funciona si hay un OTP accesible; el feed no se publica.

## Express Roosevelt (Innovate GUA, feed aparte)

`python build_express.py` genera `gtfs_express/` y `express_gtfs_draft.zip` para las rutas **R10, R11, R13 y R14** (agencia
`INNOVATE`, rutas `EX10`…, paradas `ex_*`, servicios `EX_*`; se carga junto a los otros feeds con `otp/run.sh`).
Innovate publica una tabla con direcciones sueltas, los horarios y un cartel PDF por ruta con el recorrido dibujado sobre un mapa
satelital (rojo = ida, azul = vuelta) y las paradas numeradas; **no hay coordenadas ni KML**. Cómo se reconstruyó:
1. Se georreferencia el mapa del cartel con paradas que coinciden con puntos conocidos (estaciones de Transmetro, centros comerciales
   de OpenStreetMap) y se afina alineando el trazo dibujado con la red de calles de OSM (error medio a las calles: 4–8 m).
2. Cada sentido se rehace como un camino sobre las calles de OSM que sigue el trazo dibujado y pasa por las paradas en orden,
   eligiendo el lado de la calle de cada parada con una búsqueda conjunta (`express_route.py`).
3. La posición de cada parada es el punto del camino junto a su círculo numerado.
La longitud resultante de la R10 (15.8 km ida, 15.6 km vuelta) coincide con la tabla del cartel (15.7 y 15.5 km).

**Estimado o supuesto:** frecuencias (15 min entre semana, 20 sábado, 30 domingo), velocidad (22 km/h + 20 s por parada) y el color de
las rutas. Los horarios sí son los publicados. Las posiciones son aproximadas (decenas de metros) y algunos tramos de R11, R13 y R14 dan
rodeos que habría que revisar. Quedan fuera R11A y las demás rutas Express; sus tablas ya están en `reference/Express/stops_table.json`.

## Carpetas de referencia

`reference/Transmetro/` (páginas de las líneas 1, 2, 6, 7, 12, 13 y 18 con sus KML), `reference/Tubus/` (índice de TuBus, ruta 5 y rutas 104, 105, 305, 402, 801, 802 con sus KML) y `reference/Express/` (página de rutas de Innovate, carteles PDF, tablas y extracto de OpenStreetMap). Son privadas: solo los KML y `SOURCES.txt` van en el archivo cifrado.

## TuBus (feed aparte)

`python build_tubus.py` genera `gtfs_tubus/` y `tubus_gtfs_draft.zip` a partir de `reference/Tubus/`. Es un feed **separado** del de
Transmetro pero con identificadores propios (agencia `TUBUS`, rutas `TB5`, `TB104`…, paradas `tb_NNN`, servicios `TB_WEEKDAY`…), así que
se pueden cargar juntos (OpenTripPlanner lee varios zips; `otp/run.sh` ya lo hace) o fusionar concatenando archivos.
Rutas: 5, 104, 105, 305, 402, 801 y 802; cada una con dos sentidos (`direction_id` 0 y 1).

**Fuentes (todas de las páginas de la Municipalidad):**
- KML de cada ruta (Google My Maps): trazado y coordenadas de las paradas.
- Diagramas de cada ruta (`Mapa-*.png`, `*rutayestaciones.png`): orden de paradas de cada sentido (columna derecha = ida desde la primera
  terminal; columna izquierda = regreso), transcrito a mano en `SEQ` dentro de `build_tubus.py`.
- Imágenes "Horarios de servicio": lunes a sábado 5:30–19:00; domingo y festivos 6:00–18:00 (inicio y fin en las paradas extremo).
- Colores: iconos de cada ruta.

**Estimado o supuesto (no publicado):**
- Frecuencias: 10 min en horas pico (06–09 y 17–20), 15 min el resto, sábado 15 y domingo 20; velocidad 16 km/h + 20 s por parada.
- Ruta 5 (estaciones con nombre): las plataformas Norte/Sur se asignan ida = Norte, regreso = Sur. Solo Palacio de los Deportes está
  confirmado por las direcciones del diagrama (24 calle y 9ª av. = Norte); Cipreses y Jardines de la Asunción siguen el mismo criterio.
- El diagrama de la ruta 104 coloca #61 entre #54 y #55 y #62 entre #29 y #30; #128 (ruta 105) y #84 (ruta 402) forman parte de su ruta.

## Carpetas de referencia

`reference/Transmetro/` (páginas de las líneas 1, 2, 6, 7, 12, 13 y 18 con sus KML), `reference/Tubus/` (índice de TuBus, ruta 5 y rutas 104, 105, 305, 402, 801, 802 con sus KML) y `reference/Express/` (página de rutas de Innovate, carteles PDF, tablas y extracto de OpenStreetMap). Son privadas: solo los KML y `SOURCES.txt` van en el archivo cifrado.

## TuBus (feed aparte)

`python build_tubus.py` genera `gtfs_tubus/` y `tubus_gtfs_draft.zip` a partir de `reference/Tubus/` (KML de cada ruta: trazado y
paradas numeradas). Es un feed **separado** del de Transmetro pero con identificadores propios (agencia `TUBUS`, rutas `TB5`, `TB104`…,
paradas `tb_NNN`, servicios `TB_WEEKDAY`…), así que se pueden cargar juntos (OpenTripPlanner lee varios zips; `otp/run.sh` ya lo hace)
o fusionar concatenando archivos. Rutas: 5, 104, 105, 305, 402, 801 y 802.

**Supuestos (la Municipalidad no publica horarios, frecuencias ni sentidos de TuBus):**
- Orden de paradas = numeración de la Municipalidad, que va en el orden de recorrido; cada ruta es un circuito (ida y vuelta por
  sus dos costados) que cierra en la primera parada. La ruta 5 usa estaciones con nombre: el orden sigue el trazado y las plataformas
  Norte/Sur se asignan al costado por el que pasa el recorrido.
- Ruta 104: las paradas #61 y #62 están fuera de secuencia en el mapa; se reubican donde menos distancia añaden.
- Rutas 105 y 402: se omiten #128 y #84 (paradas compartidas con otras rutas que aparecen en su mapa).
- Horario 05:00–20:00 (sáb. 05:30–19:00, dom. 06:00–19:00); frecuencia 10 min en horas pico (06–09 y 17–20), 15 min el resto, sábado 15 y
  domingo 20; velocidad 16 km/h + 20 s por parada. Todo esto es **estimado**.

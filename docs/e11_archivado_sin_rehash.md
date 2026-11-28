# E11 — Conciliación de archivado sin relectura MD5

La extracción conserva el MD5 inicial del documento original en `meta_uuid`. La auditoría ya **no recalcula MD5** de los documentos archivados ni de los documentos duplicados que permanecen en el directorio de origen. No abre esos documentos para comprobar su contenido y no existe un modo alternativo de rehash.

Por cada fila del CSV se verifica que el UUID tenga forma válida y sea único en el lote; el log debe registrar un traslado para su `meta_fuente`; el origen declarado debe estar bajo la raíz de entrada; el destino debe estar bajo la raíz de archivado, ser un archivo regular existente, no ser un enlace simbólico y no estar reutilizado por otra fila. Se concilian además número de filas, traslados registrados, contadores e inventario residual. Para duplicados se comprueba únicamente que la ruta informada siga siendo un archivo regular dentro del origen; no se compara contenido.

**Límite explícito:** la presencia y ubicación de un archivo no prueban que sus bytes sean iguales a los del original ni que su contenido siga correspondiendo al `meta_uuid`; una alteración posterior del archivado ya no se detecta mediante MD5 en esta fase. E26 debe resolver la ventana de documento movido sin log y las garantías de recuperación ante interrupción; E11 no afirma durabilidad eléctrica ni identidad criptográfica del archivo archivado.

**Pruebas sintéticas:** se impidió cualquier llamada a `hashlib.file_digest` durante la auditoría de un lote válido; un destino archivado ausente y una completitud discordante producen `ERROR`. La prueba integrada de archivado sigue comprobando presencia y trazabilidad.

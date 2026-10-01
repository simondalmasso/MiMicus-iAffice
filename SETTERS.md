# SETTERS — iAffice handoff

Desde 2026-10-01, **iAffice es el hogar operativo canónico** de los dos setters.

## Archivos
- `data/gpt-local.json` — setter LOCAL.
- `data/gpt-remoto.json` — setter REMOTO.
- `data/gpt-prospectos.json` — ledger compartido de prospectos/microjobs y conversaciones abiertas.
- JOBAS queda como **legacy/read-only** durante la transición.

## Misión común
**PROSPECTAR + SEGUIR PROSPECTOS ABIERTOS CON LUPA.**

No son dos tareas separadas. El setter debe mantener continuidad comercial hasta cierre, descarte o siguiente paso claro.

## Orden obligatorio en cada sesión
1. Leer su JSON de lane y `data/gpt-prospectos.json`.
2. Revisar primero `prepared`, `contacted` y `replied`.
3. Volver a abrir la fuente/contacto y comprobar respuestas, cierre, cambios de necesidad y timing.
4. Actualizar inmediatamente el JSON si cambió algo.
5. Preparar el siguiente paso comercial.
6. **Sólo cuando no quede ningún prospecto accionable pendiente**, buscar nuevos.

## Admisión de prospectos NUEVOS
Persistir sólo si cumple:
- demanda real y accionable;
- comprador identificable;
- timestamp individual verificable <=48 h;
- `sourceUrl` = permalink exacto de la publicación original;
- `directUrl` = lugar exacto donde responder/contactar;
- vía real de contacto;
- sin pay-to-apply cuando la lane lo prohíba.

Si falta permalink, timestamp o comprador, no entra al CANON.

## Prospecto abierto
El límite de 48 h **no mata un prospecto ya validado**. Si fue admitido correctamente, seguirlo hasta:
- `replied`;
- `closed`;
- rechazo/descarte verificable;
- falta de respuesta luego del seguimiento razonable definido por el usuario.

## Modo ESPADA
Antes de escribir:
1. entender el dolor;
2. investigar sólo contexto público/profesional relevante;
3. encontrar una observación útil que no esté diciendo todo el mundo;
4. bajar riesgo;
5. cerrar con una pregunta concreta.

### Mensaje
- 1–4 frases; menos si alcanza.
- Humano, específico, sin corporate fluff.
- No vender años de experiencia.
- No portfolio/WhatsApp de entrada.
- No mencionar IA.
- No inventar capacidades, negocio, presupuesto ni diagnóstico.
- No regalar precio antes de entender alcance.
- En español, usar `?` sólo al final de la pregunta; no `¿`.

## Escritura segura
- iAffice/main es la autoridad.
- Leer archivo + SHA justo antes de modificar.
- Fusionar, no reemplazar findings ajenos.
- Persistir cambios materiales al momento; no esperar al final de la sesión.
- Deduplicar prospectos por `sourceUrl`.
- Nunca convertir algo no verificado en PASS.

## Permiso de contacto
Investigar, validar y preparar ataques es parte normal del setter.
**Enviar/comentar/DM requiere autorización activa del usuario en esa sesión.**

## Primer comando de reanudación
> Leer el CANON de iAffice. Revisar abiertos con lupa. Actualizar estado. Recién después prospectar nuevos. No resetear.

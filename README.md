# Archivador automático de TikTok LIVE

Este proyecto comprueba periódicamente una lista de usuarios de TikTok y lanza una grabación cuando alguno aparece en LIVE. La grabación se guarda primero en el runner de GitHub Actions y, si se configura `rclone`, se copia automáticamente a Google Drive.

> **Uso responsable:** solo archiva emisiones que tengas derecho a conservar. El proyecto no está afiliado a TikTok. La librería de captura utiliza interfaces no oficiales y puede dejar de funcionar si TikTok cambia su servicio o aplica bloqueos regionales.

## Arquitectura

1. `monitor.yml` se ejecuta cada cinco minutos y llama a `TikTokLiveClient.is_live()` para cada usuario.
2. Para cada usuario activo se dispara `record.yml` mediante `workflow_dispatch`.
3. La ejecución de grabación usa [TikTok Live Recorder](https://github.com/Michele0303/TikTok-Live-Recorder), una herramienta open source mantenida, y FFmpeg.
4. El grabador escribe el flujo a disco y solo convierte a MP4 cuando termina el LIVE; esto reduce el riesgo de producir un archivo incompleto por mantener todo en memoria.
5. El MP4 terminado se copia a Google Drive. También se conserva como artifact temporal de recuperación durante tres días.

TikTok no ofrece actualmente un webhook público general para avisar que cualquier creador comenzó un LIVE. Por eso el sistema usa sondeo. La librería `TikTokLive` documenta que el cliente es no oficial y que `is_live()` es preferible a abrir una conexión completa solo para comprobar el estado.

## Alternativas consideradas

| Enfoque | Ventajas y compromisos | Coste | Complejidad |
|---|---|---:|---:|
| **GitHub Actions + Google Drive** (este proyecto) | Gratis y sin servidor propio; sondeo cada cinco minutos y grabaciones de hasta 5 h 40 min por ejecución. No es un proceso 24/7 y una emisión excepcionalmente larga puede requerir unir segmentos. | $0, más el almacenamiento que consuma la cuenta de Drive | Media |
| VM cloud siempre encendida + FFmpeg | Mejor continuidad y menos riesgo de cortes por límite de job; requiere administrar Linux, red, reinicios y el almacenamiento. Una VM de capa gratuita puede dejar de ser gratuita por región, cuota, tráfico o cambios del proveedor. | Potencialmente $0 dentro de una cuota, pero no garantizado | Alta |

Para el requisito de **coste total cero**, se implementa la primera alternativa. Si la prioridad cambia a continuidad absoluta 24/7, la arquitectura correcta es una VM persistente, pero ya no se puede prometer que sea totalmente gratuita.

## Configuración en GitHub

Crea un **repositorio público** para que los minutos de los runners estándar sean gratuitos según la documentación de GitHub. No subas credenciales al repositorio.

Copia estos archivos y configura:

| Tipo | Nombre | Valor |
|---|---|---|
| Variable de repositorio | `TIKTOK_USERS` | Lista separada por comas, por ejemplo `usuario_a,usuario_b` |
| Variable de repositorio | `DRIVE_REMOTE_PATH` | `gdrive:tiktok-live` o una ruta equivalente del remote |
| Secret de repositorio | `RCLONE_CONFIG_B64` | Configuración `rclone.conf` codificada en Base64 |

Después habilita Actions y ejecuta manualmente **Monitor TikTok LIVE** una vez para probarlo.

### Configurar Google Drive con rclone

En un equipo donde puedas completar el login OAuth:

```bash
rclone config
# New remote -> nombre: gdrive
# Storage: Google Drive
# Completa el navegador OAuth y acepta el acceso a tu Drive
rclone config file
base64 -w0 ~/.config/rclone/rclone.conf
```

Guarda la salida como el secret `RCLONE_CONFIG_B64`. El remote puede usar el almacenamiento de tu cuenta de Google; el espacio disponible y las cuotas son los de esa cuenta, no los de GitHub. La suscripción Google AI Pro puede aportar más almacenamiento de Drive, pero no elimina los límites de ejecución de GitHub Actions ni los cambios/bloqueos de TikTok.

## Integridad y emisiones largas

Una ejecución está limitada deliberadamente a aproximadamente **5 h 40 min** (`20400` segundos), por debajo del límite operativo del runner. Si el LIVE termina antes, se produce un solo MP4 continuo para esa emisión. Si continúa más tiempo, el siguiente sondeo puede iniciar otra ejecución y se producirán segmentos; únelos sin recodificar:

```bash
sudo apt-get install ffmpeg
python merge_segments.py ./segmentos ./LIVE_completo.mp4
```

Los nombres de salida contienen fecha y hora, así que el orden lexicográfico es cronológico. El comando usa `-c copy`: no recodifica y, por tanto, no degrada la calidad ni necesita cargar el vídeo en memoria. Para máxima integridad, no reduzcas el `timeout-minutes` y conserva la copia de Drive antes de borrar los artifacts.

## Coste y límites reales

| Componente | Coste esperado | Límite relevante |
|---|---:|---|
| GitHub Actions en repositorio público | Gratis en runners estándar | Las ejecuciones pueden cancelarse por límites de plataforma; una grabación individual se limita aquí a 5 h 40 min |
| Google Drive | Depende del plan/cuenta | El vídeo consume almacenamiento y está sujeto a cuotas de Drive/API |
| TikTokLive + FFmpeg | Software libre | Interfaces no oficiales, cambios de TikTok, CAPTCHA y restricciones regionales |

No recomiendo una VM de GCP como requisito de una solución “totalmente gratuita”: la elegibilidad, región, red, disco y políticas de la cuenta pueden variar, y una VM realmente permanente no resuelve por sí sola el coste del almacenamiento de vídeo. GitHub Actions es adecuado como solución gratuita de baja frecuencia, pero no equivale a un servidor 24/7.

## Diagnóstico

- Si no se inicia ninguna grabación, revisa `TIKTOK_USERS`, que el nombre no incluya la URL completa y los logs de `monitor.yml`.
- Si aparece un bloqueo regional, configura un proxy compatible en el workflow y pásalo al grabador con `-proxy`; no se incluye uno gratuito porque los proxies públicos son inestables y pueden comprometer credenciales.
- Si Google Drive falla, revisa `RCLONE_CONFIG_B64`, `DRIVE_REMOTE_PATH` y el artifact temporal del workflow.
- Si TikTok cambia su protocolo, actualiza el commit de `TikTok-Live-Recorder` y prueba manualmente antes de dejarlo desatendido.

## Referencias

- [TikTokLive](https://github.com/isaackogan/TikTokLive), cliente Python no oficial y licencia AGPL modificada.
- [TikTok Live Recorder](https://github.com/Michele0303/TikTok-Live-Recorder), grabador Python/FFmpeg bajo licencia MIT.
- [GitHub Actions: facturación](https://docs.github.com/billing/managing-billing-for-github-actions/about-billing-for-github-actions).
- [GitHub Actions: límites](https://docs.github.com/en/actions/reference/limits).
- [TikTok Webhooks](https://developers.tiktok.com/doc/webhooks-overview/), documentación oficial; no describe un evento público general de inicio de LIVE.

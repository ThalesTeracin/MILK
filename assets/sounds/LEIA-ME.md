# Sons da Milk

## latido.wav

O latido que a Milk toca quando você pede ("Milk, late", "dá um latido").
O caminho é definido em `milk/core/config.py` (`BARK_FILE`) e o volume em
`config/settings.json` (`latido.volume`).

Origem: trecho de 0,64 s (dois latidos) recortado de
*Maltese dog barking sound effect*, do Orange Free Sounds
(http://www.orangefreesounds.com/), sob licença
**Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**.
Uso não comercial, com atribuição.

Formato: WAV mono, 44100 Hz, PCM de 16 bits — é o que o `QSoundEffect` toca
direto, sem cair na reserva do `QMediaPlayer`. Um WAV em outro formato até
funciona, mas passa pelo caminho mais lento.

Para trocar o som, basta substituir o arquivo por outro WAV com o mesmo nome.
Nada no código precisa mudar.

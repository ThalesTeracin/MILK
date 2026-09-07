# Quadros da Milk caminhando

Enquanto esta pasta estiver vazia, a Milk anda pela tela como o PNG parado,
com o balanço procedural (quique, inclinação e espelhamento). As patinhas
**não** se mexem — o `milk_avatar.png` é ela sentada e de frente, e desse
desenho não há ciclo de caminhada para extrair.

Coloque a arte aqui e ela passa a mexer as patinhas sozinha, sem mudar
nenhuma linha de código.

## O que pedir para quem fizer a arte

- **A mesma Milk**: maltês branca, laço rosa na cabeça, coleira rosa com
  plaquinha de ossinho. Ela precisa continuar sendo reconhecível como a
  cachorrinha do `milk_avatar.png`.
- **De perfil**, caminhando para a **direita**. O código espelha sozinho
  quando ela vai para a esquerda — não precisa de uma versão virada.
- **Fundo transparente de verdade** (alfa), não fundo branco.
- **Ciclo fechado**: o último quadro tem que emendar no primeiro sem
  solavanco.
- **6 a 8 quadros** é o suficiente para uma caminhada convincente.
- **Todos os quadros do mesmo tamanho**, com ela sempre apoiada na mesma
  linha do chão. Se ela subir e descer entre os quadros, vai parecer que
  a imagem está tremendo.

## Formatos aceitos (o primeiro encontrado vence)

1. `andando.webp` — animação com transparência de verdade. **É o melhor.**
2. `andando.gif` — funciona, mas o GIF só liga ou desliga o pixel, então a
   borda dela pode sair serrilhada sobre o papel de parede.
3. `andando.png` — folha de sprites: quadros quadrados lado a lado, todos
   do mesmo tamanho, altura da folha igual à altura do quadro.
4. `andando/01.png`, `andando/02.png`, ... — um arquivo por quadro, em
   ordem de nome. Aceita `.png` e `.webp`.

Quadro muito esticado é descartado na carga: quase sempre é folha fatiada
errado, e desenhar aquilo na tela é pior do que continuar com o PNG parado.

## Como conferir depois de colocar

```
.venv\Scripts\python.exe -m unittest discover -s tests
.venv\Scripts\python.exe milk.py
```

Ela deve mexer as patinhas enquanto caminha e voltar ao PNG sentado quando
parar. A velocidade dos quadros acompanha a distância percorrida: se ela
freia para chegar, as patas freiam junto.

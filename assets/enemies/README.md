# Enemy portrait sources

Three single-pose transparent PNGs generated with OpenAI ImageGen for Classic
Chef. These are generated assets, not hand-drawn team sprite frames or ripped
game graphics. The original PNG files are retained; Arcade crops transparent
padding at load time and renders them on the game's shared pixel grid.

Shared prompt: one production sprite, static pose, fully visible, transparent
background, warm low top-down pixel art, dark brown outline, muted palette,
chunky square clusters, sharp scaling, no text or scenery; compatible with a
chibi chef in a wood and mint-green restaurant kitchen.

- `ghost.png`: cute round ivory kitchen ghost, lavender shadows, tiny arms,
  mischievous face and floating tail, front view. The selected generated design
  is a ghost chef with a little hat and apron, tying it to the restaurant.
- `blocker.png`: stocky male customer, wide belly, mustard waistcoat, cream
  shirt, burgundy bow tie, brown hair, moustache, dark trousers and brown shoes,
  arms folded, front view.
- `vampire.png`: whimsical small vampire, dark suit, burgundy cape, pale face,
  dark hair and small fangs, flying left with the cape trailing right. Facing
  right uses a rendering mirror of the same sprite.

Float, travel, warning markers, smoke pixels and stun stars are code-driven
effects. See `docs/SHIFT_AND_ENEMIES.md` for tuning and integration.

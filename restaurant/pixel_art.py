"""One pixel grid for the room, chef and food; text stays at screen resolution.

Artwork is rendered at 608 x 352 then enlarged with nearest-neighbour sampling.
This is a display choice, not a change to movement, hit boxes or source images.
"""
import arcade
from arcade.gl import geometry

from restaurant.display import artwork_viewport
from restaurant.shared.settings import WINDOW_HEIGHT, WINDOW_WIDTH

PIXEL_SIZE = 2
ART_SIZE = (WINDOW_WIDTH // PIXEL_SIZE, WINDOW_HEIGHT // PIXEL_SIZE)

QUAD_VERTEX = """#version 330
in vec2 in_vert;
in vec2 in_uv;
out vec2 uv;
void main() {
    gl_Position = vec4(in_vert, 0.0, 1.0);
    uv = in_uv;
}
"""
QUAD_FRAGMENT = """#version 330
uniform sampler2D artwork;
in vec2 uv;
out vec4 pixel;
void main() { pixel = texture(artwork, uv); }
"""
SPRITE_VERTEX = """#version 330
uniform WindowBlock { mat4 projection; mat4 view; } window;
uniform vec4 rectangle;
in vec2 in_vert;
in vec2 in_uv;
out vec2 uv;
void main() {
    vec2 position = rectangle.xy + in_vert * rectangle.zw * 0.5;
    gl_Position = window.projection * window.view * vec4(position, 0.0, 1.0);
    uv = vec2(in_uv.x, 1.0 - in_uv.y);
}
"""
SPRITE_FRAGMENT = """#version 330
uniform sampler2D artwork;
in vec2 uv;
out vec4 pixel;
void main() {
    vec4 sample_color = texture(artwork, uv);
    // A clean silhouette instead of a translucent fringe around the chef.
    if (sample_color.a < 0.5) discard;
    // Recover local contrast lost when the supplied frames were reduced.
    // Ignore transparent neighbours so the outline never gains a black halo.
    vec2 step_size = 1.0 / vec2(textureSize(artwork, 0));
    vec4 left = texture(artwork, uv - vec2(step_size.x, 0.0));
    vec4 right = texture(artwork, uv + vec2(step_size.x, 0.0));
    vec4 below = texture(artwork, uv - vec2(0.0, step_size.y));
    vec4 above = texture(artwork, uv + vec2(0.0, step_size.y));
    float weight = left.a + right.a + below.a + above.a;
    vec3 average = (left.rgb * left.a + right.rgb * right.a
                    + below.rgb * below.a + above.rgb * above.a) / max(weight, 0.001);
    if (weight > 0.0)
        sample_color.rgb = clamp(sample_color.rgb + 0.45 * (sample_color.rgb - average), 0.0, 1.0);
    // A shared modest colour precision keeps gradients from looking airbrushed.
    pixel = vec4(floor(sample_color.rgb * 31.0 + 0.5) / 31.0, 1.0);
}
"""


class PixelCanvas:
    """Owns the small art framebuffer. Create once, reuse each frame."""
    def __init__(self, window):
        self.window = window
        self.ctx = window.ctx
        self.texture = self.ctx.texture(ART_SIZE, filter=(self.ctx.NEAREST, self.ctx.NEAREST))
        self.framebuffer = self.ctx.framebuffer(color_attachments=[self.texture])
        self.camera = arcade.Camera2D(
            viewport=arcade.LBWH(0, 0, *ART_SIZE), position=(0, 0),
            projection=arcade.LRBT(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT),
            render_target=self.framebuffer)
        self.quad = geometry.quad_2d_fs()
        self.program = self.ctx.program(vertex_shader=QUAD_VERTEX, fragment_shader=QUAD_FRAGMENT)
        self.program["artwork"] = 0

    def begin(self):
        self.camera.use()
        self.framebuffer.clear(color=(24, 37, 44, 255))

    def present(self):
        self.ctx.screen.use()
        self.ctx.screen.clear(color=(24, 37, 44, 255))
        # Arcade's screen framebuffer applies the desktop pixel ratio itself.
        # The offscreen target above uses actual texels; the screen uses logical units.
        viewport = artwork_viewport(self.window)
        self.ctx.viewport = viewport.lbwh
        self.ctx.disable(self.ctx.BLEND)
        self.texture.use(0)
        self.quad.render(self.program)


class _SpritePainter:
    def __init__(self, window):
        self.ctx = window.ctx
        self.quad = geometry.quad_2d_fs()
        self.program = self.ctx.program(vertex_shader=SPRITE_VERTEX, fragment_shader=SPRITE_FRAGMENT)
        self.program["artwork"] = 0
        self.textures = {}

    def draw(self, texture, rectangle):
        # Crops are recreated when days change. Their content key stays stable,
        # so restarting does not retain another copy of every image on the GPU.
        key = texture.cache_name
        if key not in self.textures:
            # Upload the original Arcade image unchanged. Sampling and silhouette
            # cleanup happen on the GPU; no generated/recoloured asset files.
            gpu = self.ctx.texture((texture.width, texture.height),
                                   data=texture.image.tobytes(),
                                   filter=(self.ctx.LINEAR, self.ctx.LINEAR))
            self.textures[key] = gpu
        gpu = self.textures[key]
        # Enlarge exact pixels; only reduce high-resolution source art once.
        enlarged = (rectangle.width / PIXEL_SIZE >= texture.width
                    and rectangle.height / PIXEL_SIZE >= texture.height)
        sampling = self.ctx.NEAREST if enlarged else self.ctx.LINEAR
        gpu.filter = sampling, sampling
        gpu.use(0)
        snap = lambda value: round(value / PIXEL_SIZE) * PIXEL_SIZE
        self.program["rectangle"] = (snap(rectangle.x), snap(rectangle.y),
                                      snap(rectangle.width), snap(rectangle.height))
        self.ctx.disable(self.ctx.BLEND)
        self.quad.render(self.program)


def draw_pixel_texture(texture, rectangle):
    """Draw artwork with the same edge treatment as every other kitchen sprite."""
    window = arcade.get_window()
    if not hasattr(window, "pixel_painter"):
        window.pixel_painter = _SpritePainter(window)
    window.pixel_painter.draw(texture, rectangle)

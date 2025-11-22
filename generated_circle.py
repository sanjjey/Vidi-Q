from manim import *
from manim_voiceover import VoiceoverScene
from manim_voiceover.services.gtts import GTTSService

class Circle(VoiceoverScene):
    def construct(self):
        self.set_speech_service(GTTSService(lang="en"))
        self.camera.background_color = "#2d3c4c"

        # 1. The Hook (Approx. 5 seconds)
        hook_text = "Have you ever wondered how we mathematically define the elegant curve of a circle? The equation of a circle is fundamental to geometry and physics, precisely capturing this perfect shape."
        title = Text("The Equation of a Circle", color=BLUE_B).scale(1.2)
        intro_circle = Circle(radius=1.5, color=WHITE).shift(DOWN * 0.5)

        with self.voiceover(text=hook_text) as tracker:
            self.play(Write(title), run_time=tracker.duration * 0.6)
            self.play(FadeIn(intro_circle), run_time=tracker.duration * 0.4)
        self.play(FadeOut(title), FadeOut(intro_circle))

        # 2. Foundational Concepts (Approx. 6 seconds)
        foundational_text = "A circle is simply a set of all points in a plane that are equidistant from a fixed central point. This fixed distance is called the radius, and the central point is known as the center."
        
        center_dot = Dot(ORIGIN, color=RED)
        center_label = Text("Center (h,k)", font_size=28, color=RED).next_to(center_dot, DOWN, buff=0.2)
        radius_line = Line(ORIGIN, RIGHT * 2.5, color=YELLOW)
        radius_label = Text("Radius r", font_size=28, color=YELLOW).next_to(radius_line, UP, buff=0.2)
        definition_circle = Circle(radius=2.5, color=WHITE)

        with self.voiceover(text=foundational_text) as tracker:
            self.play(FadeIn(center_dot), Write(center_label), run_time=tracker.duration * 0.3)
            self.play(GrowFromCenter(radius_line), Write(radius_label), run_time=tracker.duration * 0.3)
            self.play(Create(definition_circle), run_time=tracker.duration * 0.4)
        self.play(FadeOut(center_dot), FadeOut(center_label), FadeOut(radius_line), FadeOut(radius_label), FadeOut(definition_circle))

        # 3. The Core Idea & 4. The Intuitive Explanation (Approx. 7 seconds)
        core_idea_text = "Using the distance formula, we can derive its equation: (x-h) squared plus (y-k) squared equals r squared. Here, (x, y) is any point on the circle, (h, k) is the center, and r is the radius."
        
        axes = Axes(
            x_range=[-4, 4, 1], y_range=[-4, 4, 1], 
            x_length=8, y_length=8, 
            axis_config={"include_numbers": False, "font_size": 24}
        ).to_edge(LEFT, buff=0.8)
        self.add(axes) # Add to scene, but don't play animation immediately for subtle background

        general_center_pt = Dot(axes.c2p(1, 1), color=RED)
        general_center_tex = MathTex("(h, k)", color=RED).next_to(general_center_pt, DL, buff=0.2)
        point_on_circle_pt = Dot(axes.c2p(3, 2.7), color=GREEN_B)
        point_on_circle_tex = MathTex("(x, y)", color=GREEN_B).next_to(point_on_circle_pt, UR, buff=0.2)
        radius_segment_v = Line(general_center_pt.get_center(), point_on_circle_pt.get_center(), color=YELLOW_B)
        radius_tex_r = MathTex("r", color=YELLOW_B).next_to(radius_segment_v, UP, buff=0.1)
        
        general_equation = MathTex("(x - h)^2 + (y - k)^2 = r^2", color=WHITE).scale(1.1).to_edge(RIGHT, buff=0.8)
        
        with self.voiceover(text=core_idea_text) as tracker:
            self.play(Create(axes), run_time=tracker.duration * 0.1) # Briefly animate axes creation
            self.play(FadeIn(general_center_pt), Write(general_center_tex), run_time=tracker.duration * 0.2)
            self.play(FadeIn(point_on_circle_pt), Write(point_on_circle_tex), run_time=tracker.duration * 0.2)
            self.play(Create(radius_segment_v), Write(radius_tex_r), run_time=tracker.duration * 0.2)
            self.play(Write(general_equation), run_time=tracker.duration * 0.3)
        self.play(FadeOut(general_center_pt), FadeOut(general_center_tex), FadeOut(point_on_circle_pt), 
                  FadeOut(point_on_circle_tex), FadeOut(radius_segment_v), FadeOut(radius_tex_r))

        # 5. A Key Example or Application (Approx. 6 seconds)
        example_text = "For instance, a circle centered at the origin (0,0) with a radius of 3 has the simplified equation x-squared plus y-squared equals 3 squared, or simply x-squared plus y-squared equals 9."
        
        origin_center_tex = MathTex("(0, 0)", color=RED).next_to(axes.c2p(0,0), DL, buff=0.2)
        radius_val_tex = MathTex("r=3", color=YELLOW_B).next_to(axes.c2p(1.5,0), UP, buff=0.1)
        example_circle = Circle(radius=3, color=BLUE_B).move_to(axes.c2p(0,0))
        
        eq_origin_general = MathTex("x^2 + y^2 = r^2", color=WHITE).scale(1.1).move_to(general_equation)
        eq_specific_r_val = MathTex("x^2 + y^2 = 3^2", color=WHITE).scale(1.1).move_to(general_equation)
        eq_final_example = MathTex("x^2 + y^2 = 9", color=WHITE).scale(1.1).move_to(general_equation)

        with self.voiceover(text=example_text) as tracker:
            self.play(ReplacementTransform(general_equation, eq_origin_general), run_time=tracker.duration * 0.15)
            self.play(Write(origin_center_tex), run_time=tracker.duration * 0.15)
            self.play(Write(radius_val_tex), run_time=tracker.duration * 0.15)
            self.play(Create(example_circle), run_time=tracker.duration * 0.25)
            self.play(ReplacementTransform(eq_origin_general, eq_specific_r_val), run_time=tracker.duration * 0.15)
            self.play(Transform(eq_specific_r_val, eq_final_example), run_time=tracker.duration * 0.15)
        self.play(FadeOut(origin_center_tex), FadeOut(radius_val_tex), FadeOut(example_circle), FadeOut(eq_specific_r_val))

        # 6. The Summary (Approx. 4 seconds)
        summary_text = "This elegant formula powerfully describes every point on a circle, from cosmic orbits to engineering designs. It's truly a cornerstone of mathematics!"
        
        final_circle_visual = Circle(radius=2, color=BLUE_C)
        final_summary_title = Text("The Equation of a Circle", font_size=36, color=WHITE).shift(UP * 0.7)
        final_formula_display = MathTex("(x - h)^2 + (y - k)^2 = r^2", color=YELLOW_A).next_to(final_summary_title, DOWN, buff=0.4)
        
        self.play(FadeOut(axes)) # Fade out axes before final elements
        with self.voiceover(text=summary_text) as tracker:
            self.play(Create(final_circle_visual), run_time=tracker.duration * 0.3)
            self.play(Write(final_summary_title), run_time=tracker.duration * 0.3)
            self.play(Write(final_formula_display), run_time=tracker.duration * 0.4)
        self.play(FadeOut(final_circle_visual), FadeOut(final_summary_title), FadeOut(final_formula_display))
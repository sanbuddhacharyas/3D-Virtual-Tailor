import svgpathtools as svgpath
from copy import deepcopy

# Custom
import pygarment as pyg

# other assets
from . import bands


class PantPanel(pyg.Panel):
    def __init__(self, name, body, design) -> None:
        """
            Basic pant panel with option to be fitted (with darts) or ruffled at waist area.
        """
        super().__init__(name)

        pant_width = design['width']['v'] * body['hips'] / 4
        low_width = pant_width * design['flare']['v']  
        length = design['length']['v'] * body['leg_length']

        waist = body['waist'] / 4
        hips_depth = body['hips_line']
        dart_position = body['bust_points'] / 2
        dart_depth = hips_depth * 0.8 

        # Crotch cotrols
        crotch_depth_diff =  body['crotch_hip_diff']
        crotch_extention = body['leg_circ'] / 2 - body['hips'] / 4

        # eval pants shape
        # amount of extra fabric at waist
        w_diff = pant_width - waist   # Assume its positive since waist is smaller then hips
        # We distribute w_diff among the side angle and a dart 
        hw_shift = w_diff / 3

        right = pyg.esf.curve_3_points(
            [
                min(- (low_width - pant_width), (pant_width - low_width) / 2),   # extend wide pants out
                0
            ],    
            [
                hw_shift, 
                length + hips_depth
            ],
            target=[0, length]
        )

        top = pyg.Edge(
            right.end, 
            [w_diff + waist, length + hips_depth] 
        )

        crotch = pyg.CurveEdge(
            top.end,
            [pant_width + crotch_extention, length - crotch_depth_diff], 
            [[0.9, -0.3]]    # NOTE: relative contols allow adaptation to different bodies
        )

        # Apply the rise
        # NOTE applying rise here for correctly collecting the edges
        rise = design['rise']['v']
        if not pyg.utils.close_enough(rise, 1.):
            new_level = top.end[1] - (1 - rise) * hips_depth
            right, top, crotch = self.apply_rise(new_level, right, top, crotch)

        left = pyg.CurveEdge(
            crotch.end,
            [
                min(pant_width, pant_width - (pant_width - low_width) / 2), 
                min(0, length - crotch_depth_diff)], 
            [[0.2, -0.1]]
        )

        self.edges = pyg.EdgeSequence(right, top, crotch, left).close_loop()
        bottom = self.edges[-1]

        # Default placement
        self.set_pivot(crotch.end)
        self.translation = [-0.5, - hips_depth - crotch_depth_diff + 5, 0] 

        # Out interfaces (easier to define before adding a dart)
        self.interfaces = {
            'outside': pyg.Interface(self, right),
            'crotch': pyg.Interface(self, crotch),
            'inside': pyg.Interface(self, left),
            'bottom': pyg.Interface(self, bottom)
        }

        # Add top dart 
        dart_width = w_diff - hw_shift
        dart_shape = pyg.esf.dart_shape(dart_width, dart_depth)
        top_edges, dart_edges, int_edges = pyg.ops.cut_into_edge(
            dart_shape, top, offset=(hw_shift + waist - dart_position), right=True)

        self.edges.substitute(top, top_edges)
        self.stitching_rules.append((pyg.Interface(self, dart_edges[0]), pyg.Interface(self, dart_edges[1])))

        self.interfaces['top'] = pyg.Interface(self, int_edges)   

    def apply_rise(self, level, right, top, crotch):

        right_c, crotch_c = right.as_curve(), crotch.as_curve()
        cutout = svgpath.Line(0 + 1j*level, crotch.end[0] + 1j*level)

        right_intersect = right_c.intersect(cutout)[0]
        right_cut = right_c.cropped(0, right_intersect[0])
        new_right = pyg.CurveEdge.from_svg_curve(right_cut)

        c_intersect = crotch_c.intersect(cutout)[0]
        c_cut = crotch_c.cropped(c_intersect[0], 1)
        new_crotch = pyg.CurveEdge.from_svg_curve(c_cut)

        new_top = pyg.Edge(new_right.end, new_crotch.start)

        return new_right, new_top, new_crotch



class PantsHalf(pyg.Component):
    def __init__(self, tag, body, design) -> None:
        super().__init__(tag)
        design = design['pants']

        self.front = PantPanel(
            f'pant_f_{tag}', body, design
            ).translate_by([0, body['waist_level'] - 5, 25])
        self.back = PantPanel(
            f'pant_b_{tag}', body, design
            ).translate_by([0, body['waist_level'] - 5, -20])

        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces['outside'], self.back.interfaces['outside']),
            (self.front.interfaces['inside'], self.back.interfaces['inside'])
        )

        # add a cuff
        if design['cuff']['type']['v']:
            
            pant_bottom = pyg.Interface.from_multiple(
                    self.front.interfaces['bottom'], self.back.interfaces['bottom'])

            # Copy to avoid editing original design dict
            cdesign = deepcopy(design)
            cdesign['cuff']['b_width'] = {}
            cdesign['cuff']['b_width']['v'] = pant_bottom.edges.length() / design['cuff']['top_ruffle']['v']

            # Init
            cuff_class = getattr(bands, cdesign['cuff']['type']['v'])
            self.cuff = cuff_class(tag, cdesign)

            # Position
            self.cuff.place_by_interface(
                self.cuff.interfaces['top'],
                pant_bottom,
                gap=5
            )

            # Stitch
            self.stitching_rules.append((
                pant_bottom,
                self.cuff.interfaces['top'])
            )

        self.interfaces = {
            'crotch_f': self.front.interfaces['crotch'],
            'crotch_b': self.back.interfaces['crotch'],
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
        }

class Pants(pyg.Component):
    def __init__(self, body, design) -> None:
        super().__init__('Pants')


        self.right = PantsHalf('r', body, design)
        self.left = PantsHalf('l', body, design).mirror()

        self.stitching_rules = pyg.Stitches(
            (self.right.interfaces['crotch_f'], self.left.interfaces['crotch_f']),
            (self.right.interfaces['crotch_b'], self.left.interfaces['crotch_b']),
        )

        self.interfaces = {
            'top_f': pyg.Interface.from_multiple(
                self.right.interfaces['top_f'], self.left.interfaces['top_f']),
            'top_b': pyg.Interface.from_multiple(
                self.right.interfaces['top_b'], self.left.interfaces['top_b']),
            # Some are reversed for correct connection
            'top': pyg.Interface.from_multiple(   # around the body starting from front right
                self.right.interfaces['top_f'],
                self.left.interfaces['top_f'].reverse(),
                self.left.interfaces['top_b'],   
                self.right.interfaces['top_b'].reverse()),
        }

class WBPants(pyg.Component):
    def __init__(self, body, design) -> None:
        super().__init__('WBPants')

        self.pants = Pants(body, design)

        # pants top
        wb_len = (self.pants.interfaces['top_b'].projecting_edges().length() + 
                    self.pants.interfaces['top_f'].projecting_edges().length())

        self.wb = bands.WB(body, design)
        self.wb.translate_by([0, self.wb.width + 2, 0])

        self.stitching_rules = pyg.Stitches(
            (self.pants.interfaces['top'], self.wb.interfaces['bottom']),
        )


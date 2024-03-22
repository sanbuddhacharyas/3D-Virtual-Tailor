# Custom
import pygarment as pyg
from scipy.spatial.transform import Rotation as R
import numpy as np

# other assets
from .bands import WB
from .shapes import Sun

# Panels
class SkirtPanel(pyg.Panel):
    """One panel of a panel skirt with ruffles on the waist"""

    def __init__(self, name, waist_length=70, length=70, ruffles=1, bottom_cut=0, flare=0) -> None:
        super().__init__(name)

        base_width = waist_length / 2
        top_width = base_width * ruffles
        low_width = top_width + 2*flare
        x_shift_top = (low_width - top_width) / 2  # to account for flare at the bottom

        # define edge loop
        self.right = pyg.esf.side_with_cut([0,0], [x_shift_top, length], start_cut=bottom_cut / length) if bottom_cut else pyg.EdgeSequence(pyg.Edge([0,0], [x_shift_top, length]))
        self.waist = pyg.Edge(self.right[-1].end, [x_shift_top + top_width, length])
        self.left = pyg.esf.side_with_cut(self.waist.end, [low_width, 0], end_cut=bottom_cut / length) if bottom_cut else pyg.EdgeSequence(pyg.Edge(self.waist.end, [low_width, 0]))
        self.bottom = pyg.Edge(self.left[-1].end, self.right[0].start)
        
        # define interface
        self.interfaces = {
            'right': pyg.Interface(self, self.right[-1]),
            'top': pyg.Interface(self, self.waist, ruffle=ruffles).reverse(True),
            'left': pyg.Interface(self, self.left[0]),
            'bottom': pyg.Interface(self, self.bottom)
        }
        # Single sequence for correct assembly
        self.edges = self.right
        self.edges.append(self.waist)  # on the waist
        self.edges.append(self.left)
        self.edges.append(self.bottom)

        # default placement
        self.top_center_pivot()
        self.center_x()  # Already know that this panel should be centered over Y


class ThinSkirtPanel(pyg.Panel):
    """One panel of a panel skirt"""

    def __init__(self, name, top_width=10, bottom_width=20, length=70) -> None:
        super().__init__(name)

        # define edge loop
        self.flare = (bottom_width - top_width) / 2
        self.edges = pyg.esf.from_verts(
            [0,0], [self.flare, length], [self.flare + top_width, length], [self.flare * 2 + top_width, 0], 
            loop=True)

        # w.r.t. top left point
        self.set_pivot(self.edges[0].end)

        self.interfaces = {
            'right': pyg.Interface(self, self.edges[0]),
            'top': pyg.Interface(self, self.edges[1]),
            'left': pyg.Interface(self, self.edges[2])
        }

class FittedSkirtPanel(pyg.Panel):
    """Fitted panel for a pencil skirt
    """
    def __init__(
        self, name, waist, hips,  
        hips_depth, length, low_width, rise=1,
        low_angle=0,
        dart_position=None,  dart_frac=0.5,
        cut=0,
        side_cut=None) -> None:
        """
        """
        super().__init__(name)

        # adjust for a rise
        adj_hips_depth = rise * hips_depth
        adj_waist = pyg.utils.lin_interpolation(hips, waist, rise)
        dart_depth = hips_depth * dart_frac
        dart_depth = max(dart_depth - (hips_depth - adj_hips_depth), 0)

        # amount of extra fabric
        w_diff = hips - adj_waist   # Assume its positive since waist is smaller then hips
        # We distribute w_diff among the side angle and a dart 
        hw_shift = w_diff / 6

        # Adjust the bottom edge to the desired angle
        angle_shift = np.tan(np.deg2rad(low_angle)) * low_width

        right = pyg.esf.curve_3_points(
            [hips - low_width, angle_shift],    
            [hw_shift, length + adj_hips_depth],
            target=[0, length]
        )
        top = pyg.Edge(right.end, [hips * 2 - hw_shift, length + adj_hips_depth])
        left = pyg.esf.curve_3_points(
            top.end,
            [hips + low_width, -angle_shift],
            target=[hips * 2, length]
        )
        self.edges = pyg.EdgeSequence(right, top, left).close_loop()
        bottom = self.edges[-1]

        if cut:  # add a cut
            # Use long and thin disconnected dart for a cutout
            new_edges, _, int_edges = pyg.ops.cut_into_edge(
                pyg.esf.dart_shape(2, depth=cut * length),    # 1 cm 
                bottom, 
                offset= bottom.length() / 2,
                right=True)

            self.edges.substitute(bottom, new_edges)
            bottom = int_edges

        if side_cut is not None:
            # Add a stylistic cutout to the skirt
            new_edges, _, int_edges = pyg.ops.cut_into_edge(
                side_cut,    
                left, 
                offset=left.length() / 2,   
                right=True)

            self.edges.substitute(left, new_edges)
            left = int_edges

        # Default placement
        self.top_center_pivot()
        self.translation = [-hips / 2, 5, 0]

        # Out interfaces (easier to define before adding a dart)
        self.interfaces = {
            'bottom': pyg.Interface(self, bottom),
            'right': pyg.Interface(self, right), 
            'left': pyg.Interface(self, left),  
        }

        # Add top darts
        dart_width = w_diff - hw_shift
        self.add_darts(top, dart_width, dart_depth, dart_position)


    def add_darts(self, top, dart_width, dart_depth, dart_position):
        
        dart_shape = pyg.esf.dart_shape(dart_width, dart_depth)
        top_edge_len = top.length()
        top_edges, dart_edges, int_edges = pyg.ops.cut_into_edge(
            dart_shape, 
            top, 
            offset=(top_edge_len / 2 - dart_position),   # from the middle of the edge
            right=True)
        
        self.stitching_rules.append(
            (pyg.Interface(self, dart_edges[0]), pyg.Interface(self, dart_edges[1])))

        left_edge_len = top_edges[-1].length()
        top_edges_2, dart_edges, int_edges_2 = pyg.ops.cut_into_edge(
            dart_shape, 
            top_edges[-1], 
            offset=left_edge_len - top_edge_len / 2 + dart_position, # from the middle of the edge
            right=True)

        self.stitching_rules.append(
            (pyg.Interface(self, dart_edges[0]), pyg.Interface(self, dart_edges[1])))
        
        # Update panel
        top_edges.substitute(-1, top_edges_2)
        int_edges.substitute(-1, int_edges_2)

        self.interfaces['top'] = pyg.Interface(self, int_edges) 
        self.edges.substitute(top, top_edges)


class PencilSkirt(pyg.Component):
    def __init__(self, body, design) -> None:
        super().__init__(self.__class__.__name__)

        design = design['pencil-skirt']
        self.design = design  # Make accessible from outside

        # Depends on leg length
        length = design['length']['v'] * body['leg_length']

        # condition
        if design['style_side_cut']['v']:
            depth = 0.7 * (body['hips'] / 4 - body['bust_points'] / 2)
            style_shape = Sun(depth * 2, depth, n_rays=6, d_rays=depth*0.2)
        else:
            style_shape = None

        self.front = FittedSkirtPanel(
            f'skirt_f',   
            body['waist'] / 4, 
            body['hips'] / 4, 
            body['hips_line'],
            length,
            low_width=design['flare']['v'] * body['hips'] / 4,
            rise=design['rise']['v'],
            low_angle=design['low_angle']['v'],
            dart_position=body['bust_points'] / 2,
            dart_frac=1.35,  # Diff for front and back
            cut=design['front_cut']['v'], 
            side_cut=style_shape
        ).translate_to([0, body['waist_level'], 25])
        self.back = FittedSkirtPanel(
            f'skirt_b', 
            body['waist'] / 4, 
            body['hips'] / 4,
            body['hips_line'],
            length,
            low_width=design['flare']['v'] * body['hips'] / 4,
            rise=design['rise']['v'],
            low_angle=design['low_angle']['v'],
            dart_position=body['bum_points'] / 2,
            dart_frac=1.1,   
            cut=design['back_cut']['v'], 
            side_cut=style_shape
        ).translate_to([0, body['waist_level'], -20])

        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = {
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
            'top': pyg.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top'].reverse()
            ),
            'bottom': pyg.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']
            )
        }


# Full garments - Components
class Skirt2(pyg.Component):
    """Simple 2 panel skirt"""
    def __init__(self, body, design, tag='') -> None:
        super().__init__(
            self.__class__.__name__ if not tag else f'{self.__class__.__name__}_{tag}')

        design = design['skirt']

        self.front = SkirtPanel(
            f'front_{tag}' if tag else 'front', 
            waist_length=body['waist'], 
            length=design['length']['v'],
            ruffles=design['ruffle']['v'],   # Only if on waistband
            flare=design['flare']['v'],
            bottom_cut=design['bottom_cut']['v'] * design['length']['v']
        ).translate_to([0, body['waist_level'], 25])
        self.back = SkirtPanel(
            f'back_{tag}'  if tag else 'back', 
            waist_length=body['waist'], 
            length=design['length']['v'],
            ruffles=design['ruffle']['v'],   # Only if on waistband
            flare=design['flare']['v'],
            bottom_cut=design['bottom_cut']['v'] * design['length']['v']
        ).translate_to([0, body['waist_level'], -20])

        self.stitching_rules = pyg.Stitches(
            (self.front.interfaces['right'], self.back.interfaces['right']),
            (self.front.interfaces['left'], self.back.interfaces['left'])
        )

        # Reusing interfaces of sub-panels as interfaces of this component
        self.interfaces = {
            'top_f': self.front.interfaces['top'],
            'top_b': self.back.interfaces['top'],
            'top': pyg.Interface.from_multiple(
                self.front.interfaces['top'], self.back.interfaces['top']
            ),
            'bottom': pyg.Interface.from_multiple(
                self.front.interfaces['bottom'], self.back.interfaces['bottom']
            )
        }

# With waistband
class SkirtWB(pyg.Component):
    def __init__(self, body, design) -> None:
        super().__init__(f'{self.__class__.__name__}')

        self.wb = WB(body, design)
        self.skirt = Skirt2(body, design)
        self.skirt.place_below(self.wb)

        self.stitching_rules = pyg.Stitches(
            (self.wb.interfaces['bottom'], self.skirt.interfaces['top'])
        )
        self.interfaces = {
            'top': self.wb.interfaces['top'],
            'bottom': self.skirt.interfaces['bottom']
        }


class SkirtManyPanels(pyg.Component):
    """Round Skirt with many panels"""

    def __init__(self, body, design) -> None:
        super().__init__(f'{self.__class__.__name__}_{design["flare-skirt"]["n_panels"]["v"]}')

        waist = body['waist']    # Fit to waist

        design = design['flare-skirt']
        n_panels = design['n_panels']['v']

        # Length is dependent on length of legs
        length = body['hips_line'] + design['length']['v'] * body['leg_length']

        flare_coeff_pi = 1 + design['suns']['v'] * length * 2 * np.pi / waist

        self.front = ThinSkirtPanel('front', panel_w:=waist / n_panels,
                                    bottom_width=panel_w * flare_coeff_pi,
                                    length=length )
        self.front.translate_to([-waist / 4, body['waist_level'], 0])
        # Align with a body
        self.front.rotate_by(R.from_euler('XYZ', [0, -90, 0], degrees=True))
        self.front.rotate_align([-waist / 4, 0, panel_w / 2])
        
        # Create new panels
        self.subs = pyg.ops.distribute_Y(self.front, n_panels, odd_copy_shift=15)

        # Stitch new components
        for i in range(1, n_panels):
            self.stitching_rules.append((self.subs[i - 1].interfaces['left'], self.subs[i].interfaces['right']))
            
        self.stitching_rules.append((self.subs[-1].interfaces['left'], self.subs[0].interfaces['right']))

        # Define the interface
        self.interfaces = {
            'top': pyg.Interface.from_multiple(*[sub.interfaces['top'] for sub in self.subs])
        }

class SkirtManyPanelsWB(pyg.Component):
    def __init__(self, body, design) -> None:
        super().__init__(f'{self.__class__.__name__}')

        wb_width = 5
        self.skirt = SkirtManyPanels(body, design).translate_by([0, -wb_width, 0])
        self.wb = WB(body, design).translate_by([0, wb_width, 0])

        self.stitching_rules.append(
            (self.skirt.interfaces['top'], self.wb.interfaces['bottom']))



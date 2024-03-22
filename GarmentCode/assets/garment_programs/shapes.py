"""A decorative shapes"""


# Custom
import pygarment as pyg

def sample_arc(curve, length, stride, n_points, shift=0):
    ts = [(shift + i*stride) / length for i in range(n_points)]
    verts = [curve.point(t) for t in ts]

    for i in range(len(verts)):
        verts[i] = [verts[i].real, verts[i].imag]

    return verts

def Sun(width, depth, n_rays=8, d_rays=5):
    """Sun-like mark"""

    # Outer arc
    out_arc = pyg.CircleEdge.from_three_points(
        [0, 0], [width, 0], [width/2, depth]
    )
    in_arc = pyg.CircleEdge.from_three_points(
        [d_rays, 0], [width - d_rays, 0], [width/2, depth - d_rays]
    )
    out_curve = out_arc.as_curve()
    in_curve = in_arc.as_curve()

    # Sample with stride
    out_stride = out_arc.length() / n_rays
    in_stride = in_arc.length() / n_rays
    
    out_verts = sample_arc(out_curve, out_arc.length(), out_stride, n_rays, out_stride / 2)
    in_verts = sample_arc(in_curve, in_arc.length(), in_stride, n_rays + 1, 0)

    # Mix the vertices in the right order
    verts = out_verts
    for i in range(len(in_verts)):
        verts.insert(i*2, in_verts[i])

    return pyg.esf.from_verts(*verts)


if __name__ == '__main__':
    Sun(30, 15)
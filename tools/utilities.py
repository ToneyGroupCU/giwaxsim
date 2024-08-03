import numpy as np
import re

def parse_config_file(file_path):
    config = {}
    with open(file_path, 'r') as f:
        for line in f:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                config[key] = value
    return config

def strip_numbers(element):
        match = re.match(r"([a-zA-Z]+)", element)
        return match.group(1) if match else element

def load_xyz(xyz_path):
    """
    Parameters:
    - xyz_path: string, path to xyz file of molecule, NP, etc

    Returns:
    -coords: 2D numpy array of x,y,z coordinates
    -elements: 1D numpy array of element species for each coord in coords
    """
    # Extracting the atomic symbols and positions from the xyz file
    with open(xyz_path, 'r') as file:
        lines = file.readlines()
    # Extracting atom data
    atom_data = [line.split() for line in lines[2:] if len(line.split()) == 4]
    symbols, coords = zip(*[(strip_numbers(parts[0]), np.array(list(map(float, parts[1:])))) for parts in atom_data])

    coords = np.array(coords)
    elements = np.array(symbols)
    
    return coords, elements

def load_pdb(pdb_path):
    """
    Parameters:
    - pdb_path: string, path to pdb file of molecule, protein, etc.

    Returns:
    - coords: 2D numpy array of x, y, z coordinates
    - elements: 1D numpy array of element species for each coord in coords
    """
    coords = []
    elements = []

    # Open and read the PDB file
    with open(pdb_path, 'r') as file:
        for line in file:
            if line.startswith("ATOM") or line.startswith("HETATM"):
                # Extracting the relevant information from ATOM/HETATM lines
                element = line[76:78].strip()  # Element symbol, typically in columns 77-78
                x = float(line[30:38])  # X coordinate, typically in columns 31-38
                y = float(line[38:46])  # Y coordinate, typically in columns 39-46
                z = float(line[46:54])  # Z coordinate, typically in columns 47-54

                elements.append(element)
                coords.append([x, y, z])

    coords = np.array(coords)
    elements = np.array(elements)
    
    return coords, elements


def write_xyz(output_path, coords, elements):
    """
    Writes the molecular structure to an xyz file at the specified path.
    
    Parameters:
    - output_path: string, path where the xyz file will be saved
    - coords: 2D numpy array of x, y, z coordinates
    - elements: 1D numpy array of element symbols corresponding to each row in coords
    """
    if len(coords) != len(elements):
        raise ValueError("Length of coordinates and elements must be the same.")

    # Start writing to the file
    with open(output_path, 'w') as file:
        # Write the number of atoms on the first line
        file.write(f"{len(elements)}\n")
        # Write a comment or blank line on the second line
        file.write("XYZ file generated by write_xyz function\n")

        # Write elements and coordinates to the file
        for element, (x, y, z) in zip(elements, coords):
            file.write(f"{element} {x:.8f} {y:.8f} {z:.8f}\n")

def rotation_matrix(u,theta):
    '''
    Generates a rotation matrix given a unit vector and angle
    see https://en.wikipedia.org/wiki/Rotation_matrix#Rotation_matrix_from_axis_and_angle

    Input
      u = unit vector in 3d cartesian coords about which the rotation will occur
      theta = angle in rad to rotate
    '''
    ux = u[0]
    uy = u[1]
    uz = u[2]
    R = np.zeros((3,3))
    R[0,0] = np.cos(theta)+ux**2*(1-np.cos(theta))
    R[0,1] = ux*uy*(1-np.cos(theta))-uz*np.sin(theta)
    R[0,2] = ux*uz*(1-np.cos(theta))+uy*np.sin(theta)
    R[1,0] = uy*ux*(1-np.cos(theta))+uz*np.sin(theta)
    R[1,1] = np.cos(theta)+uy**2*(1-np.cos(theta))
    R[1,2] = uy*uz*(1-np.cos(theta))-ux*np.sin(theta)
    R[2,0] = uz*ux*(1-np.cos(theta))-uy*np.sin(theta)
    R[2,1] = uz*uy*(1-np.cos(theta))+ux*np.sin(theta)
    R[2,2] = np.cos(theta)+uz**2*(1-np.cos(theta))
    
    return R

def gaussian_kernel(size, sigma=1):
    """ 
    Returns a normalized 3D gauss kernel array for convolutions
    see https://math.stackexchange.com/questions/434629/3-d-generalization-of-the-gaussian-point-spread-function
    
    """
    size = int(size) // 2
    x, y, z = np.mgrid[-size:size+1, -size:size+1, -size:size+1]
    C = 1/(sigma**3 * (2*np.pi)**(3/2))
    g = C*np.exp(-(x**2 + y**2 + z**2) / (2 * sigma**2))
    
    return g, size

def fft_gaussian(qx_axis, qy_axis, qz_axis, sigma):
    """
    Returns the fft of a gaussian in 3D q-space.

    inputs:
    - qx_axis: 1D numpy array of qx axis values
    - qy_axis: 1D numpy array of qy axis values
    - qz_axis: 1D numpy array of qz axis values
    - sigma: realspace sigma value for gaussian
    """
    sigma *= 1/(2*np.pi)
    qx, qy, qz = np.meshgrid(qx_axis, qy_axis, qz_axis)
    g_fft = np.exp(-2*np.pi**2*sigma**2 * (qx**2 + qy**2 + qz**2))
    
    return g_fft

def calc_real_space_abc(a_mag, b_mag, c_mag, alpha_deg, beta_deg, gamma_deg):
    '''
    https://www.ucl.ac.uk/~rmhajc0/frorth.pdf
    '''
    alpha = np.deg2rad(alpha_deg)
    beta = np.deg2rad(beta_deg)
    gamma = np.deg2rad(gamma_deg)
    
    V = a_mag*b_mag*c_mag*np.sqrt(1-np.cos(alpha)**2-np.cos(beta)**2-np.cos(gamma)**2+2*np.cos(alpha)*np.cos(beta)*np.cos(gamma)) 
    
    ax = a_mag
    ay = 0
    az = 0
    a = np.array([ax, ay, az])
    
    bx = b_mag*np.cos(gamma)
    by = b_mag*np.sin(gamma)
    bz = 0
    b = np.array([bx, by, bz])
    
    cx = c_mag*np.cos(beta)
    cy = c_mag*(np.cos(alpha)-np.cos(beta)*np.cos(gamma))/(np.sin(gamma))
    cz = V/(a_mag*b_mag*np.sin(gamma))
    c = np.array([cx, cy, cz])
    
    return a, b, c

def rotate_coords_z(coords, phi):
    # Convert phi to radians
    phi_rad = np.radians(phi)
    
    # Define the rotation matrix for rotation about the z-axis
    rotation_matrix = np.array([
        [np.cos(phi_rad), -np.sin(phi_rad), 0],
        [np.sin(phi_rad), np.cos(phi_rad), 0],
        [0, 0, 1]
    ])
    
    # Apply the rotation matrix to each coordinate
    rotated_coords = np.dot(coords, rotation_matrix.T)
    
    return rotated_coords
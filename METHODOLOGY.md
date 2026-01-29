# 1. Methodology

This section details the rigorous reverse engineering process employed to decipher the proprietary communication protocol of the Samsung Galaxy Buds and the mathematical framework established to utilize the extracted sensor data for spatial interaction.

## 3.1 Protocol Reverse Engineering

The absence of public documentation for the Galaxy Buds' spatial sensor necessitated a black-box reverse engineering approach using **traffic sniffing** and **differential cryptanalysis** techniques.

### 3.1.1 Traffic Acquisition (HCI Sniffing)
Bluetooth traffic was intercepted at the Host Controller Interface (HCI) layer. By enabling the *Bluetooth HCI Snoop Log* on a host Android device and interacting with the official companion application, we captured `BTHCI_ACL` (Asynchronous Connection-Listed) packets. 

Analysis of the `btsnoop_hci.log` using Wireshark identified a specific RFCOMM channel (Channel 27) exhibiting high-frequency throughput (~1.2 kbps) exclusively when the "Head Tracking" feature was active.

### 3.1.2 Packet Structure Analysis
The raw binary stream was analyzed for repeating patterns and delimiters. We identified a consistent packet structure compliant with a custom implementation of the Serial Port Profile (SPP).

**Definition 1 (Packet Schema)**: Let $P$ be a data packet. The structure is defined as:
$$
P = \langle \text{SOM}, L, \text{ID}, \mathbf{D}, \text{CRC} \rangle
$$
Where:
*   $\text{SOM} = \mathtt{0xFD}$ (Start of Message delimiter).
*   $L \in \mathbb{N}_{<2^{10}}$ is the payload length (10 bits).
*   $\text{ID} \in \{\mathtt{0x01}, \mathtt{0x02}, \dots\}$ is the message type identifier.
*   $\mathbf{D} = [d_0, d_1, \dots, d_{n-1}]$ is the payload vector of $n$ bytes.
*   $\text{CRC}$ is a 16-bit Cyclic Redundancy Checksum.

### 3.1.3 Differential Payload Analysis
To decode the payload $\mathbf{D}$ for Message ID `0x01` (IMU Data), we performed differential analysis by isolating physical device states:

1.  **Stationary State ($S_0$)**: $\Delta \mathbf{D} \approx 0$ (noise only).
2.  **Rotational State ($S_{rot}$)**: Significant variation in specific byte clusters.

We mapped the 16-byte payload to four 32-bit floating-point variables using the IEEE 754 standard (Little Endian):
$$
\mathbf{D}_{\mathtt{0x01}} \mapsto \{q_w, q_x, q_y, q_z\} \in \mathbb{R}^4
$$
This confirmed the transmission of a normalized **Quaternion** vector representing device orientation.

## 3.2 Mathematical Modeling

The system state is represented in $\mathbb{R}^3$ Euclidean space using Quaternions to avoid gimbol lock singularities inherent in Euler angle representations.

### 3.2.1 Quaternion Kinematics
The orientation of the device frame $F_B$ relative to the reference frame $F_W$ is defined by the unit quaternion $\mathbf{q}$:

$$
\mathbf{q} = w + xi + yj + zk, \quad \|\mathbf{q}\| = 1
$$

### 3.2.2 Attitude Conversion (Quaternion to Euler)
For visualization and interface mapping, the quaternion $\mathbf{q}$ is decomposed into intrinsic Tait-Bryan angles ($z-y'-x''$ sequence): Yaw ($\psi$), Pitch ($\theta$), and Roll ($\phi$).

The conversion equations derived are:

1.  **Yaw ($\psi$)**:
    $$ \psi = \operatorname{atan2}(2(q_w q_z + q_x q_y), 1 - 2(q_y^2 + q_z^2)) $$

2.  **Pitch ($\theta$)**:
    $$ \theta = \arcsin(2(q_w q_y - q_z q_x)) $$
    *Domain adjustment*: The term $2(q_w q_y - q_z q_x)$ is clamped to $[-1, 1]$ to handle numerical precision errors.

3.  **Roll ($\phi$)**:
    $$ \phi = \operatorname{atan2}(2(q_w q_x + q_y q_z), 1 - 2(q_x^2 + q_y^2)) $$

## 3.3 Multimodal Fusion Framework

To establish a comprehensive Human-Computer Interaction (HCI) model, we integrated the inertial head tracking data with computer vision-based hand tracking.

### 3.3.1 Projection Mapping
We define a projection function $f: \mathbb{S}^2 \rightarrow \mathbb{R}^2$ mapping the spherical angular coordinates $(\psi, \theta)$ to the planar screen coordinates $(x_s, y_s)$:

$$
\begin{bmatrix} x_s \\ y_s \end{bmatrix} = \begin{bmatrix} C_x \\ C_y \end{bmatrix} + k \begin{bmatrix} 1 & 0 \\ 0 & -1 \end{bmatrix} \begin{bmatrix} \psi - \psi_{ref} \\ \theta - \theta_{ref} \end{bmatrix}
$$

Where:
*   $(C_x, C_y)$ is the screen centroid.
*   $k$ is the sensitivity gain ($\text{px}/\text{deg}$).
*   $(\psi_{ref}, \theta_{ref})$ represents the calibrated zero-orientation vector.

### 3.3.2 Gesture Recognition Logic
Hand gestures are classified using topological constraints on 21 hand landmarks extracted via MediaPipe. We define a gesture $G$ as a function of the landmark set $\mathcal{L}$:

**Fist Gesture (Drag Mode)**:
$$ G_{fist}(\mathcal{L}) \iff \forall f \in \{I, M, R, P\}, \|\mathbf{p}_{tip}^f - \mathbf{p}_{wrist}\| < \|\mathbf{p}_{mcp}^f - \mathbf{p}_{wrist}\| $$

This inequality asserts that for all fingers ($f$), the Euclidean distance from the fingertip to the wrist is strictly less than the distance from the metacarpophalangeal (MCP) joint to the wrist, geometrically validating a closed fist.

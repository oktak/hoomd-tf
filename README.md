Tensorflow Plugin
==============

This plugin allows using tensorflow to compute forces in a simulation
or to compute other quantities, like collective variables to fit a
potential for coarse-graining. You must first construct your
tensorlfow graph using the `tensorflow_plugin.graphbuilder` class and
then add the `tensorflow` compute to your hoomd simulation.

Building Graph
=====

To construct a graph, construct a graphbuilder:

```
from hoomd.tensorflow_plugin import GraphBuilder
graph = GraphBuilder(N, NN, output_forces)
```

where `N` is the number of particles in the simulation, `NN` is the maximum number of nearest neighbors to consider, and `output_forces` indicates if the graph will output forces to use in the simulation. After building the `graph`, it will have three tensors as attributes to use in constructing the tensorflow graph: `nlist`, `positions`, and `forces`. `nlist` is an `N` x `NN` x 4 tensor containing the nearest neighbors. An entry of all zeros indicates that less than `NN` nearest neighbors where present for a particular particle. The 4 right-most dimensions are `x,y,z` and `w`, which is the particle type. Note that the `x,y,z` values are a vector originating at the particle and ending at its neighbor. `positions` and `forces` are `N` x 4 tensors. `forces` *only* is available if the graph does not output forces via `output_forces=False`.

Computing Forces
-----
If you graph is outputting forces, you may either compute forces and pass them to `GraphBuilder.save(...)` or have them computed via automatic differentiation of a potential energy. Call `GraphBuilder.compute_forces(energy)` where `energy` is a scalar or tensor that depends on `nlist` and/or `positions`. A tensor of forces will be returned as sum(-dE / dn) - dE / dp where the sum is over the neighbor list. For example, to compute a `1 / r` potential:

```
graph = hoomd.tensorflow_plugin.GraphBuilder(N, N - 1)
#remove w since we don't care about types
nlist = graph.nlist[:, :, :3]
#get r
r = tf.norm(nlist, axis=2)
#compute 1. / r while safely treating r = 0.
# halve due to full nlist
rij_energy = 0.5 * graph.safe_div(1, r)
#sum over neighbors
energy = tf.reduce_sum(rij_energy, axis=1)
forces = graph.compute_forces(energy)
```

See in the above example that we have used the
`GraphBuilder.safe_div(numerator, denominator)` function which allows
us to safely treat a `1 / 0` due to using nearest neighbor distances,
which can arise because `nlist` contains 0s for when less than `NN`
nearest neighbors are found. Note that because `nlist` is a *full*
neighbor list, you should divide by 2 if your energy is a sum of
pairwise energies.

Virial
-----

The virial is computed and added to the graph if you use the
`compute_forces` function and your energy has a non-zero derivative
with respect to `nlist`. You may also explicitly pass the virial when
saving, or pass `None` to remove the automatically calculated virial.

Finalizing the Graph
----

To finalize and save your graph, you must call the `GraphBuilder.save(directory, force_tensor=forces, virial = None, out_node=None)` function. `force_tensor` should be your computed forces, either as computed by your graph or as the output from `compute_energy`. If your graph is not outputting forces, then you must provide a tensor which will be computed, `out_node`, at each timestep. Your forces should be an `N x 4` tensor with the 4th column indicating per-particle potential energy. The virial should be an `N` x 3 x 3 tensor.

Complete Examples
-----

See `tensorflow_plugin/models/test-models/build.py` for more.

### Lennard-Jones

```
graph = hoomd.tensorflow_plugin.GraphBuilder(N, NN)
nlist = graph.nlist[:, :, :3]
#get r
r = tf.norm(nlist, axis=2)
#compute 1 / r while safely treating r = 0.
#pairwise energy. Double count -> divide by 2
p_energy = 4.0 / 2.0 * (graph.safe_div(1., r**12) - graph.safe_div(1., r**6))
#sum over pairwise energy
energy = tf.reduce_sum(p_energy, axis=1)
forces = graph.compute_forces(energy)
graph.save(force_tensor=forces, model_directory='/tmp/lj-model')
```



Using Graph in a Simulation
=====

You may use a saved tensorflow model via:

```
import hoomd
from hoomd.tensorflow_plugin import tensorflow

#must construct prior to initialization
tfcompute = tensorflow(model_loc)

...hoomd initialization code...

nlist = hoomd.md.nlist.cell()
tfcompute.attach(nlist, r_cut=r_cut, force_mode='output')

```

where `model_loc` is the directory where the tensorflow model was saved, `nlist` is a hoomd neighbor list object, `r_cut` is the maximum distance for to consider particles as being neighbors, and `force_mode` is a string that indicates how to treat forces. A value of `'output'` indicates forces will be output from hoomd and input into the tensorflow model. `'add'` means the forces output from the tensorflow model should be added with whatever forces are computed from hoomd, for example if biasing a simulation. `'ignore'` means the forces will not be modified and are not used the tensorflow model, for example if computing collective variables that do not depend on forces. `'overwrite'` means the forces from the tensorflow model will overwrite the forces from hoomd, for example if the tensorflow model is computing the forces instead.

Examples
-----
See `tensorflow_plugin/test-py/test_tensorflow.py`

Note on Building and Executing Tensorflow Models in Same Script
------

Due to the side-effects of importing tensorflow, you must build and save your graph in a separate python process first before running it hoomd.

Requirements
=====
* Latest tensorflow (cuda 9.0, cudnn7)
* numpy
* HOOMD


Docker Image for Development
====

To use the included docker image:

```
docker build -t hoomd-tf tensorflow_plugin
```

To run the container:

```
docker run --rm -it --cap-add=SYS_PTRACE --security-opt seccomp=unconfined  -v tensorflow_plugin/:/srv/hoomd-blue/tensorflow_plugin hoomd-tf bash
```

The `cap--add` and `security-opt` flags are optional and allow `gdb` debugging.

Once in the container:

```
cd /srv/hoomd-blue && mkdir build && cd build
cmake .. -DCMAKE_CXX_FLAGS=-march=native -DCMAKE_BUILD_TYPE=Debug -DCMAKE_C_FLAGS=-march=native -DENABLE_CUDA=OFF -DENABLE_MPI=OFF -DBUILD_HPMC=off -DBUILD_CGCMM=off -DBUILD_MD=on -DBUILD_METAL=off -DBUILD_TESTING=off -DBUILD_DEPRECATED=off -DBUILD_MPCD=OFF
make -j2
```

To run the unit tests after make:
```
python ../tensorflow-plugin/test-py/test_tensorflow.py
```

If you change C++/C code, remake. If you modify python code, copy the new version to the build directory.


Issues
====
* Energy conservation
* Domain decomposition testing

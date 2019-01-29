import hoomd, hoomd.md, hoomd.data, hoomd.init, hoomd.dump, hoomd.group
from hoomd.tensorflow_plugin import tfcompute
import tensorflow as tf
from sys import argv as argv
from math import sqrt
import numpy as np
import os, pickle
import matplotlib.pyplot as plt


training_dir = '/tmp/ann-training'
inference_dir = '/tmp/ann-inference'

#with hoomd.tensorflow_plugin.tfcompute(inference_dir, bootstrap = training_dir) as tfcompute:
    #hoomd.context.initialize()
    #make a hoomd system of just 2 particles and generate U(r)
    # rcut = 5.0
    # snapshot = hoomd.data.make_snapshot(N=2, particle_types=['A'], box=hoomd.data.boxdim(L=5))
    # snapshot.particles.position[0] = [0.,0.,0.]
    # snapshot.particles.position[1] = [0.01,0.,0.]
    # snapshot.particles.velocity[1] = [1., 0., 0.]
    #hoomd.init.read_snapshot(snapshot)
    #all_atoms = hoomd.group.all()
    #nlist = hoomd.md.nlist.cell(check_period = 1)
    #tfcompute.attach(nlist, r_cut=rcut)
    #hoomd.md.integrate.nve(group=all_atoms, limit=None)#, zero_force=True)
    #hoomd.analyze.log(filename='NN_potential.log',
                      # quantities = ['potential_energy', 'N', 'momentum'],
                      # period=1,
                      # overwrite=True)
    #hoomd.dump.gsd(filename='POTENTIAL_trajectory.gsd', period=10, group=hoomd.group.all(), overwrite=True)
    #hoomd.run(3000)
    #run for 3k steps and get our data
#calculated_forces = tf.get_variable('calculated_forces:0', shape = [2])
#calculated_energies = tf.get_variable('calculated_energies', shape=[2])
#tf.inspect_checkpoint.print_tensors_in_checkpoint_file('/tmp/ann-training')
tf.train.import_meta_graph(os.path.join('/tmp/ann-training/','model.meta'),import_scope='')
with open('/tmp/ann-training/graph_info.p', 'rb') as f:
    var_dict= pickle.load(f)
print(var_dict)

#fake_var = tf.get_variable('bias_b1', shape=[6])
energy_tensor = tf.get_default_graph().get_tensor_by_name('calculated_energies:0')
r_inv_tensor = tf.get_default_graph().get_tensor_by_name('r_inv:0')
nlist_tensor = tf.get_default_graph().get_tensor_by_name(var_dict['nlist'])
NN = var_dict['NN']
energy_arr = []
checkpoint_num = 200
with tf.Session() as sess:
    checkpoint_str = '/tmp/ann-training/model-{}'.format(checkpoint_num)
    checkpoint = tf.train.load_checkpoint(checkpoint_str)
    print(checkpoint)
    saver = tf.train.Saver()
    saver.restore(sess, checkpoint_str)
    pos_arr = np.linspace(0., 3.0, 300)
    np_nlist = np.zeros((2, NN, 4))
    nlist = {}
    
    for i in range(1, 300):
        np_nlist[0,0,1] = pos_arr[i]
        np_nlist[1,0,1] = -pos_arr[i]
        nlist[nlist_tensor] = np_nlist
        nlist['keep_prob:0'] = 1.0
        output = sess.run({'energy':energy_tensor}, feed_dict = nlist)
        print('pairwise energy with radius {} is :{}'.format(pos_arr[i], output['energy'][0]))
        energy_arr.append(output['energy'][0] + output['energy'][1])

energy_arr = np.array(energy_arr)
def lj_energy(r):
    return(4 * ( (r)**(-12) - (r)**(-6) ))

plt.figure()
plt.plot(pos_arr[1:], energy_arr - energy_arr[-1], label='Neural Network Potential')
plt.plot(pos_arr[1:], lj_energy(pos_arr[1:]), label='Lennard-Jones Potential')

NN_min_idx = np.argmin(energy_arr)
# if pos_arr[NN_min_idx] <= 0.2:#pointed the wrong way
#     energy_arr = -energy_arr #flip it upside-down
#     NN_min_idx = np.argmin(energy_arr)
lj_min_idx = np.argmin(lj_energy(pos_arr[1:]))
lj_min = pos_arr[lj_min_idx]
NN_min = pos_arr[NN_min_idx]

plt.scatter(NN_min, energy_arr[NN_min_idx] - energy_arr[-1], label = 'NN minimum: {:.5}'.format(NN_min))
plt.scatter(lj_min, lj_energy(lj_min), label = 'LJ minimum: {:.5}'.format(lj_min))

print('X value at min of calculated LJ: {}'.format(lj_min))
print('X value at min of Neural Net LJ: {}'.format(NN_min))

plt.ylim(-10,10)
plt.legend(loc='best')
plt.xlabel('$r\sigma$')
plt.ylabel('$U(r) / \epsilon$')
plt.savefig('step_{}_ann_potential.png'.format(checkpoint_num))
plt.savefig('step_{}_ann_potential.pdf'.format(checkpoint_num))
plt.savefig('step_{}_ann_potential.svg'.format(checkpoint_num))


plt.figure()
r_inv = 1 / pos_arr[1:]
def corresponding_energy(r_inv, energy_arr):
    return(energy_arr[np.argmin(1/pos_arr >= 1/r_inv)])


new_energy_arr = np.array([corresponding_energy(item, energy_arr) for item in r_inv])
lj_en_arr = lj_energy(pos_arr[1:])
new_lj_en_arr = np.array([corresponding_energy(item, lj_en_arr) for item in r_inv])

plt.plot(r_inv, new_energy_arr - new_energy_arr[-1], label='Neural Network Potential')
plt.plot(r_inv, new_lj_en_arr, label='Lennard-Jones Potential')

plt.scatter(NN_min, energy_arr[NN_min_idx] - energy_arr[-1], label = 'NN minimum: {:.5}'.format(NN_min))
plt.scatter(lj_min, lj_energy(lj_min), label = 'LJ minimum: {:.5}'.format(lj_min))

plt.ylim(-10,10)
plt.xlim(0, 10)
plt.legend(loc='best')
plt.xlabel('$(r\sigma)^{-1}$')
plt.ylabel('$U((r\sigma)^{-1}) / \epsilon$')
plt.savefig('step_{}_ann_potential_r_inv.svg'.format(checkpoint_num))
plt.savefig('step_{}_ann_potential_r_inv.png'.format(checkpoint_num))
plt.savefig('step_{}_ann_potential_r_inv.pdf'.format(checkpoint_num))

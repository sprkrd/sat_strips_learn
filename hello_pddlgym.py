import gym
import pddlgym
import imageio

env = gym.make("PDDLEnvSokoban-v0")
obs, debug_info = env.reset()
action = env.action_space.sample()
obs, reward, done, debug_info = env.step(action)
img = env.render()
imageio.imsave("frame1.png", img)

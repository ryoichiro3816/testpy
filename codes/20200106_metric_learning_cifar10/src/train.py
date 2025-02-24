import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from  torch.utils.data import DataLoader
import torch.optim.lr_scheduler as lr_scheduler
from torch.autograd.function import Function
import torchvision

import matplotlib.pyplot as plt
import argparse
from tqdm import trange
import numpy as np
from sklearn.metrics import classification_report

from losses import CenterLoss
from cifar10_net import Net
import cifar10_data


def main():
	args = parse_args()

	# Device
	device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

	# Dataset
	train_loader, test_loader, classes = cifar10_data.load_dataset(args.dataset_dir, img_show=False)
	
	# Model
	model = Net().to(device)
	print(model)

	# Loss
	nllloss = nn.NLLLoss().to(device)  # CrossEntropyLoss = log_softmax + NLLLoss
	loss_weight = 1
	centerloss = CenterLoss(10, 2).to(device)
	
	# Optimizer
	dnn_optimizer = optim.SGD(model.parameters(), lr=0.001, momentum=0.9, weight_decay=0.0005)
	sheduler = lr_scheduler.StepLR(dnn_optimizer, 20, gamma=0.8)
	center_optimizer = optim.SGD(centerloss.parameters(), lr =0.5)
	
	print('Start training...')
	for epoch in range(100):
		# Update parameters.
		epoch += 1
		sheduler.step()

		# Train and test a model.
		train_acc, train_loss, feat, labels = train(device, train_loader, model, nllloss, loss_weight, centerloss, dnn_optimizer, center_optimizer)
		test_acc, test_loss = test(device, test_loader, model, nllloss, loss_weight, centerloss)
		stdout_temp = 'Epoch: {:>3}, train acc: {:<8}, train loss: {:<8}, test acc: {:<8}, test loss: {:<8}'
		print(stdout_temp.format(epoch, train_acc, train_loss, test_acc, test_loss))
		
		# Visualize features of each class.
		vis_img_path = args.vis_img_path_temp.format(str(epoch).zfill(3))
		visualize(feat.data.cpu().numpy(), labels.data.cpu().numpy(), epoch, vis_img_path)

		# Save a trained model.
		model_path = args.model_path_temp.format(str(epoch).zfill(3))
		torch.save(model.state_dict(), model_path)


def train(device, train_loader, model, nllloss, loss_weight, centerloss, dnn_optimizer, center_optimizer):
	running_loss = 0.0
	pred_list = []
	label_list = []
	ip1_loader = []
	idx_loader = []
	
	model.train()
	for i,(imgs, labels) in enumerate(train_loader):
		# Set batch data.
		imgs, labels = imgs.to(device), labels.to(device)
		# Predict labels.
		ip1, pred = model(imgs)
		# Calculate loss.
		loss = nllloss(pred, labels) + loss_weight * centerloss(labels, ip1)
		# Initilize gradient.
		dnn_optimizer.zero_grad()
		center_optimizer.zero_grad()
		# Calculate gradient.
		loss.backward()
		# Upate parameters.
		dnn_optimizer.step()
		center_optimizer.step()
		# For calculation.
		running_loss += loss.item()
		pred_list += [int(p.argmax()) for p in pred]
		label_list += [int(l) for l in labels]
		# For visualization.
		ip1_loader.append(ip1)
		idx_loader.append((labels))
	
	result = classification_report(pred_list, label_list, output_dict=True)
	train_acc = round(result['weighted avg']['f1-score'], 6)
	train_loss = round(running_loss / len(train_loader.dataset), 6)
	
	feat = torch.cat(ip1_loader, 0)
	labels = torch.cat(idx_loader, 0)
	
	return train_acc, train_loss, feat, labels


def test(device, test_loader, model, nllloss, loss_weight, centerloss):
	model = model.eval()
		
	# Prediciton
	running_loss = 0.0
	pred_list = []
	label_list = []
	with torch.no_grad():
		for i,(imgs, labels) in enumerate(test_loader):
			# Set batch data.
			imgs, labels = imgs.to(device), labels.to(device)
			# Predict labels.
			ip1, pred = model(imgs)
			# Calculate loss.
			loss = nllloss(pred, labels) + loss_weight * centerloss(labels, ip1)
			# Append predictions and labels.
			running_loss += loss.item()
			pred_list += [int(p.argmax()) for p in pred]
			label_list += [int(l) for l in labels]

	# Calculate accuracy.
	result = classification_report(pred_list, label_list, output_dict=True)
	test_acc = round(result['weighted avg']['f1-score'], 6)
	test_loss = round(running_loss / len(test_loader.dataset), 6)

	return test_acc, test_loss


def visualize(feat, labels, epoch, vis_img_path):
	colors = ['#ff0000', '#ffff00', '#00ff00', '#00ffff', '#0000ff',
			  '#ff00ff', '#990000', '#999900', '#009900', '#009999']
	plt.figure()
	for i in range(10):
		plt.plot(feat[labels==i, 0], feat[labels==i, 1], '.', color=colors[i])
	plt.legend(['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'], loc='best')
	plt.xlim(left=-8, right=8)
	plt.ylim(bottom=-8, top=8)
	plt.text(-7.8, 7.3, "epoch=%d" % epoch)
	plt.savefig(vis_img_path)
	plt.clf()
	

def parse_args():
	arg_parser = argparse.ArgumentParser(description="parser for focus one")

	arg_parser.add_argument("--dataset_dir", type=str, default='D:/workspace/datasets')
	arg_parser.add_argument("--model_path_temp", type=str, default='../outputs/models/checkpoints/mnist_original_softmax_center_epoch_{}.pth')
	arg_parser.add_argument("--vis_img_path_temp", type=str, default='../outputs/visual/epoch_{}.png')
	
	args = arg_parser.parse_args()

	return args


if __name__ == "__main__":
	main()


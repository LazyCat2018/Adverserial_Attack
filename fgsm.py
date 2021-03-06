# -*- coding: utf-8 -*-
"""FGSM

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1nEPxTXJaYUGEJhDA_drEKr4kwi79BO82
"""
# ================================================== GOOGLE COLAB SETTINGS ==========================================================================
!apt-get install -y -qq software-properties-common python-software-properties module-init-tools
!wget https://launchpad.net/~alessandro-strada/+archive/ubuntu/google-drive-ocamlfuse-beta/+build/15331130/+files/google-drive-ocamlfuse_0.7.0-0ubuntu1_amd64.deb
!dpkg -i google-drive-ocamlfuse_0.7.0-0ubuntu1_amd64.deb
!apt-get install -f
!apt-get -y install -qq fuse
from google.colab import auth
auth.authenticate_user()
from oauth2client.client import GoogleCredentials
creds = GoogleCredentials.get_application_default()
import getpass
!google-drive-ocamlfuse -headless -id={creds.client_id} -secret={creds.client_secret} < /dev/null 2>&1 | grep URL
vcode = getpass.getpass()
!echo {vcode} | google-drive-ocamlfuse -headless -id={creds.client_id} -secret={creds.client_secret}

!mkdir -p drive
!google-drive-ocamlfuse drive

from os import path
from wheel.pep425tags import get_abbr_impl, get_impl_ver, get_abi_tag
platform = '{}{}-{}'.format(get_abbr_impl(), get_impl_ver(), get_abi_tag())

accelerator = 'cu80' #'cu80' if path.exists('/opt/bin/nvidia-smi') else 'cpu'
print('Platform:', platform, 'Accelerator:', accelerator)

!pip install --upgrade --force-reinstall -q http://download.pytorch.org/whl/{accelerator}/torch-0.4.0-{platform}-linux_x86_64.whl torchvision

import torch
print('Torch', torch.__version__, 'CUDA', torch.version.cuda)
print('Device:', torch.device('cuda:0'))

cd drive/Adverserial_Attacks



torch.cuda.is_available()
# ========================================== import libraries ==========================================================================================
import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.backends.cudnn as cudnn 
from torch.autograd import Variable

import torchvision
import torchvision.transforms as transforms

import pickle as pkl
import numpy as np
import matplotlib.pyplot as plt
# %matplotlib inline
# ======================================== prepare the dataset ==========================================================================================
mean_cifar10 = [0.485, 0.456, 0.406]   
std_cifar10 = [0.229, 0.224, 0.225]
batch_size = 100
transform_train = transforms.Compose([
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize(mean_cifar10,std_cifar10),
])

transform_test = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(mean_cifar10,std_cifar10),
])

trainset = torchvision.datasets.CIFAR10(root='./data', train=True, download= True, transform=transform_train)
trainloader = torch.utils.data.DataLoader(trainset, batch_size=batch_size, shuffle=True, num_workers=2)

testset = torchvision.datasets.CIFAR10(root='./data', train=False, download=True, transform=transform_test)
testloader = torch.utils.data.DataLoader(testset, batch_size=batch_size, shuffle=False, num_workers=2)

classes = ('plane', 'car', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck')

#================================================== VGG16 Network =======================================================================================
class VGG16(nn.Module):
  def __init__(self):
    super(VGG16,self).__init__()

    self.block1 = nn.Sequential(
                  nn.Conv2d(in_channels = 3,out_channels = 64,kernel_size = 3,padding = 1),
                  nn.BatchNorm2d(64),
                  nn.ReLU(),
                  nn.Conv2d(in_channels = 64,out_channels = 64,kernel_size = 3, padding =1),
                  nn.BatchNorm2d(64),
                  nn.ReLU(),
                  nn.MaxPool2d(kernel_size=2, stride=2),
                  nn.Dropout2d(0.3))

    self.block2 = nn.Sequential(
                  nn.Conv2d(in_channels = 64,out_channels = 128,kernel_size = 3,padding = 1),
                  nn.BatchNorm2d(128),
                  nn.ReLU(),
                  nn.Conv2d(in_channels = 128,out_channels = 128,kernel_size = 3, padding =1),
                  nn.BatchNorm2d(128),
                  nn.ReLU(),
                  nn.MaxPool2d(kernel_size=2, stride=2),
                  nn.Dropout2d(0.4))

    self.block3 = nn.Sequential(
                  nn.Conv2d(in_channels = 128,out_channels = 256,kernel_size = 3,padding = 1),
                  nn.BatchNorm2d(256),
                  nn.ReLU(),
                  nn.Conv2d(in_channels = 256,out_channels = 256,kernel_size = 3,padding = 1),
                  nn.BatchNorm2d(256),
                  nn.ReLU(),
                  nn.Conv2d(in_channels = 256,out_channels = 256,kernel_size = 3, padding =1),
                  nn.BatchNorm2d(256),
                  nn.ReLU(),
                  nn.MaxPool2d(kernel_size=2, stride=2),
                  nn.Dropout2d(0.4))

    self.block4 = nn.Sequential(
                  nn.Conv2d(in_channels = 256,out_channels = 512,kernel_size = 3,padding = 1),
                  nn.BatchNorm2d(512),
                  nn.ReLU(),
                  nn.Conv2d(in_channels = 512,out_channels = 512,kernel_size = 3,padding = 1),
                  nn.BatchNorm2d(512),
                  nn.ReLU(),
                  nn.Conv2d(in_channels = 512,out_channels = 512,kernel_size = 3, padding =1),
                  nn.BatchNorm2d(512),
                  nn.ReLU(),
                  nn.MaxPool2d(kernel_size=2, stride=2) ,
                  nn.Dropout2d(0.4))

    self.block5 = nn.Sequential(
                  nn.Conv2d(in_channels = 512,out_channels = 512,kernel_size = 3,padding = 1),
                  nn.BatchNorm2d(512),
                  nn.ReLU(),
                  nn.Conv2d(in_channels = 512,out_channels = 512,kernel_size = 3,padding = 1),
                  nn.BatchNorm2d(512),
                  nn.ReLU(),
                  nn.Conv2d(in_channels = 512,out_channels = 512,kernel_size = 3, padding =1),
                  nn.BatchNorm2d(512),
                  nn.ReLU(),
                  nn.MaxPool2d(kernel_size=2, stride=2),
                  nn.Dropout2d(0.5) )

    self.fc =     nn.Sequential(
                  nn.Linear(512,100),
                  nn.Dropout(0.5),
                  nn.BatchNorm1d(100),
                  nn.ReLU(),
                  nn.Dropout(0.5),
                  nn.Linear(100,10), )
                  
                  


  def forward(self,x):
    out = self.block1(x)
    out = self.block2(out)
    out = self.block3(out)
    out = self.block4(out)
    out = self.block5(out)
    out = out.view(out.size(0),-1)
    out = self.fc(out)

    return out

# ============================================= Model initialisation, Loss function and Optimizer========================================================
model = VGG16()
if torch.cuda.is_available():
  model.cuda()
criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.SGD(model.parameters(),lr = 0.001,momentum = 0.9,weight_decay = 0.006)
# schedule = torch.optim.lr_scheduler.StepLR(optimizer,step_size=20,gamma = 0.7)

state = torch.load('./model_170_85.pth')
model.load_state_dict(state['model'])

# ===============================================  Attack methods ===============================================================================

# FAST GRADIENT SIGN METHOD (FGSM)
def FGSM(test_loader,epsilon = 0.1,min_val = -1,max_val = 1):
  correct = 0                   # Fast gradient sign method
  adv_correct = 0
  misclassified = 0
  total = 0
  adv_noise =0 
  adverserial_images = []
  y_preds = []
  y_preds_adv = []
  test_images = []
  test_label = []
  
  for i, (images,labels) in enumerate(test_loader):
    if torch.cuda.is_available():
      images = images.cuda()
      labels = labels.cuda()
    images = Variable(images,requires_grad = True)
    labels = Variable(labels)
    
    outputs = model(images)
    loss =criterion(outputs,labels)

    model.zero_grad()
    if images.grad is not None:
      images.grad.data.fill_(0)
    loss.backward()
    
    grad = torch.sign(images.grad.data) # Take the sign of the gradient.
    images_adv = torch.clamp(images.data + epsilon*grad,min_val,max_val)     # x_adv = x + epsilon*grad
    
    adv_output = model(Variable(images_adv)) # output by the model after adding adverserial noise
    
    _,predicted = torch.max(outputs.data,1)      # Prediction on the clean image
    _,adv_predicted = torch.max(adv_output.data,1) # Prediction on the image after adding adverserial noise
    
    total += labels.size(0)
    correct += (predicted == labels).sum().item()
    adv_correct += (adv_predicted == labels).sum().item()
    misclassified += (predicted != adv_predicted).sum().item()
    
    adverserial_images.extend((images_adv).cpu().data.numpy())
    y_preds.extend(predicted.cpu().data.numpy())
    y_preds_adv.extend(adv_predicted.cpu().data.numpy())
    test_images.extend(images.cpu().data.numpy())
    test_label.extend(labels.cpu().data.numpy())
    
    
  np.save('adverserial_images.npy',adverserial_images)    # Save the adverserial labels, images
  np.save('y_preds.npy',y_preds)
  np.save('y_preds_adv.npy',y_preds_adv)
  np.save('test_images.npy',test_images)
  np.save('test_label.npy',test_label)
  print('Accuracy of the model w/0 adverserial attack on test images is : {} %'.format(100*correct/total))
  print('Accuracy of the model with adverserial attack on test images is : {} %'.format(100* adv_correct/total))
  print('Number of misclassified examples(as compared to clean predictions): {}/{}'.format(misclassified,total))




#  ITERATIVE - FGSM

def i_FGSM(test_loader,iterations = 1,epsilon = 0.1,min_val = -1,max_val = 1):
  correct = 0                # Iterative fast gradient sign method
  adv_correct = 0
  misclassified = 0
  total = 0 
  adverserial_images = []
  y_preds = []
  y_preds_adv = []
  test_images = []
  test_label = []
  
  for i, (images,labels) in enumerate(test_loader):
    if torch.cuda.is_available():
      images = images.cuda()
      labels = labels.cuda()
      output_clean = model(Variable(images))
    images_adv = Variable(images.data,requires_grad = True)
    # Apply the FGSM for T iterations
    for j in range(iterations):  
      if torch.cuda.is_available():
        images_adv = images_adv.cuda()
      outputs = model(images_adv)
      loss = criterion(outputs,Variable(labels))
      
      model.zero_grad()
      if images_adv.grad is not None:
        images.adv.grad.data.fill_(0)
      
      loss.backward()
      grad = torch.sign(images_adv.grad.data)   # Get the sign of the gradient
      
      images_adv = images_adv + (epsilon/iterations)*grad  # X_n+1 = X_n + (epsilon/T)*grad   T = no. of iterations
       # Clip the image 
      images_adv = torch.where(images_adv > images + epsilon,images+epsilon,images_adv)
      images_adv = torch.where(images_adv < images-epsilon,images-epsilon,images_adv)
      images_adv = torch.clamp(images_adv,min_val,max_val)
      images_adv = Variable(images_adv.data,requires_grad = True)
      

    adv_output = model(Variable(images_adv))
    
    _,predicted = torch.max(output_clean.data,1)    # Ouput of the clean image
    _,adv_predicted = torch.max(adv_output.data,1) # Output of the image after adding adverserial noise
    
    total += labels.size(0)
    correct += (predicted == labels).sum().item()
    adv_correct += (adv_predicted == labels).sum().item()
    misclassified += (predicted != adv_predicted).sum().item()
    
    adverserial_images.extend((images_adv).cpu().data.numpy())
    y_preds.extend(predicted.cpu().data.numpy())
    y_preds_adv.extend(adv_predicted.cpu().data.numpy())
    test_images.extend(images.cpu().data.numpy())
    test_label.extend(labels.cpu().data.numpy())
    
  np.save('adverserial_images.npy',adverserial_images)
  np.save('y_preds.npy',y_preds)
  np.save('y_preds_adv.npy',y_preds_adv)
  np.save('test_images.npy',test_images)
  np.save('test_label.npy',test_label)
  print('Accuracy of the model w/0 adverserial attack on test images is : {} %'.format(100*correct/total))
  print('Accuracy of the model with adverserial attack on test images is : {} %'.format(100* adv_correct/total))
  print('Number of misclassified examples(as compared to clean predictions): {}/{}'.format(misclassified,total))


# ========================================= Attack the model ============================================================================
'''  
The image lies between [0,1] but since I have trained the whole network on normalized input, Therefore the min_val = -2.117 and max_val = 2.64 and 
not {0,1}

We unnormalize the images for visualisation.

The values of epsilon has been chosen according to the normalized input

'''
i_FGSM(testloader,iterations = 15,epsilon = 0.15,min_val = -2.117,max_val = 2.64) 
# FGSM(testloader,epsilon = 0.15,min_val = -2.117,max_val = 2.64)

# ============================== Visualisation ===================================================================================================
adverserial_images = np.load('adverserial_images.npy')
y_preds = np.load('y_preds.npy')
y_preds_adv = np.load('y_preds_adv.npy')
test_images = np.load('test_images.npy')
test_label = np.load('test_label.npy')

c = adverserial_images - test_images  # Verify whether the max diff between the image and adverserial image in epsilon or not
c.max()

mean = np.array([0.485, 0.456, 0.406])
mean = mean[:,None,None]
std = np.array([0.229, 0.224, 0.225])
std = std[:,None,None]

# Get index of  all the images where the attack is succesful
attack = (y_preds != y_preds_adv)
indexes = []
for i in range(len(attack)):
  if attack[i] == True:
    indexes.append(i)

indexes = np.array(indexes)


# Plot the images 
plt_idx = 0
while plt_idx < 2:
    idx = np.random.choice(indexes)
    img = test_images[idx]
    adv_img = adverserial_images[idx]
    img = img*std + mean
    img = np.transpose(img,(1,2,0))
    img = img.clip(0,1)
   
    adv_img = adv_img*std + mean
    adv_img =np.transpose(adv_img,(1,2,0))
    adv_img = adv_img.clip(0,1)
    noise = adv_img - img
    noise = np.absolute(10*noise)  # Noise is multiplied by 10 for visualisation purpose
    noise = noise.clip(0,1)
    
    if y_preds[idx] != y_preds_adv[idx]:
        disp_im = np.concatenate((img, adv_img,noise), axis=1)
        ax = plt.subplot(1,2,plt_idx+1)
#         ax.set_title(classes[test_label[idx]],classes[y_preds[idx]], classes[y_preds_adv[idx]] )
        ax.set_title("pred: {}, adv:{}".format(y_preds[idx], y_preds_adv[idx]))
        plt.imshow(disp_im)
        plt.xticks([])
        plt.yticks([])
        plt_idx += 1
        print("True Label: ",classes[test_label[idx]]," ","Predicted Label:",classes[y_preds[idx]]," ", "Adverserial Label:",classes[y_preds_adv[idx]])
plt.show()







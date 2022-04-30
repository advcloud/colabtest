from IPython.display import display, Javascript, HTML, Audio
from io import BytesIO
from base64 import b64encode, b64decode
from uuid import uuid4
import requests
from time import sleep
import json
from os.path import join, isdir, isfile
from os import mkdir

from google.colab.output import eval_js
from PIL import Image, ImageDraw, ImageOps, ImageEnhance
import numpy as np
from scipy.io.wavfile import read as wav_read
import ffmpeg

def webcam2numpy(quality=0.8, size=(800,600)):
  """Saves images from your webcam into a numpy array.
  Returns
  -------
  numpy.ndarray
  """

  VIDEO_HTML = """
  <div class="video_container">
    <video autoplay
    width=%d height=%d></video>
    <div style='position: absolute;top: 40px; left: 40px; font-size: 40px; color: green;'>Click on the image to save!</div>
  </div>
  <script>
  var video = document.querySelector('video')
  navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream=> video.srcObject = stream)
    
  var data = new Promise(resolve=>{
    video.onclick = ()=>{
      var canvas = document.createElement('canvas')
      var [w,h] = [video.offsetWidth, video.offsetHeight]
      canvas.width = w
      canvas.height = h
      canvas.getContext('2d')
            .drawImage(video, 0, 0, w, h)
      video.srcObject.getVideoTracks()[0].stop()
      video.replaceWith(canvas)
      resolve(canvas.toDataURL('image/jpeg', %f))
    }
  })
  </script>
  """

  handle = display(HTML(VIDEO_HTML % (size[0],size[1],quality)), display_id='videoHTML')
  data = eval_js("data")
  binary = b64decode(data.split(',')[1])
  f = BytesIO(binary)
  return np.asarray(Image.open(f))


def copy2clipboard(inputFile):
  """Opens a file or URL and copies the content to the clipboard.
  """

  js1 = """
  const tmp_div = document.createElement('div');
  const tmp_button = document.createElement('button');
  tmp_button.textContent = 'Copy2Clipboard';
  document.body.appendChild(tmp_div);
  tmp_div.appendChild(tmp_button);
  const inputTXT = atob("%s");
  const el = document.createElement('textarea');
  el.style.position = 'absolute';
  el.style.left = '-9999px';
  el.value = inputTXT;
  tmp_div.appendChild(el);
  async function copy2clipboard(){
    tmp_button.focus();
    await new Promise((resolve) => tmp_button.onclick = resolve);
    el.select();
    el.focus();
    document.execCommand('copy');
    el.remove()
    tmp_div.remove();
  }"""

  try:
    with open(inputFile, 'r') as file:
        data = file.read()
        data = b64encode(bytes(data, 'utf-8')).decode("utf-8")
  except FileNotFoundError:
      try:
          request = requests.get(inputFile)
          data = request.text
          data = b64encode(bytes(data, 'utf-8')).decode("utf-8")
      except (ConnectionError, requests.exceptions.MissingSchema) as e: 
          print('File / URL site does not exist')
          print(e)
          
  display(Javascript(js1 % data))
  display(Javascript("copy2clipboard()"))


def imshow(inputImg, imgformat="PNG", windowName="imwrite", width=None, height=None):
  """Shows an image using the same named window.
  """

  JS_SRC = """
    function testImage(windowName) {
      var image  = document.getElementById(windowName);
      if (typeof(image) != 'undefined' && image != null){
        return 1;
      } else {
        return 0;
      }
    }
      
    function imwrite(newSRC, windowName) {
      var image  = document.getElementById(windowName);
      if (typeof(image) != 'undefined' && image != null){
        console.log("image was NOT null");
        image.src = newSRC;
      } else {
        console.log("image was null");
        const image = document.createElement("image");
        image.id = windowName;
        document.body.appendChild(image);
      }
      //new Promise((resolve) => image.complete = resolve);
    }
    """
  
  imageBuffer = BytesIO()

  if type(inputImg) == str:
    save_all = False
    if imgformat == 'GIF':
      save_all = True
    Image.open(inputImg).save(imageBuffer, format=imgformat, save_all=save_all)
  elif type(inputImg) == np.ndarray:
    Image.fromarray(inputImg).save(imageBuffer, format=imgformat)
  elif "PIL" in str(type(inputImg)):
    inputImg.save(imageBuffer, format=imgformat)

  imgBase64 = b64encode(imageBuffer.getvalue())
  if imgformat == 'PNG':
    str_data = "data:image/png;base64," + imgBase64.decode(encoding="utf-8")
  elif imgformat == 'JPEG' or imgformat == 'JPG':
    str_data = "data:image/jpeg;base64," + imgBase64.decode(encoding="utf-8")
  elif imgformat == 'GIF':
    str_data = "data:image/gif;base64," + imgBase64.decode(encoding="utf-8")
  else:
    raise "Wrong image format!"

  display(Javascript(JS_SRC))

  if not eval_js('testImage("%s")' % windowName):
    HTML_SRC ="""
    <div id="%s_div">
    <img id="%s" src="%s" """ % (windowName, windowName, str_data)
    if width: 
      HTML_SRC += 'width="%s" ' % str(width)
    if height:
      HTML_SRC += 'height="%s" ' % str(height)
    HTML_SRC += "/><br></div>"
    
    display(HTML(HTML_SRC))

  display(Javascript("imwrite('%s','%s')" % (str_data, windowName)))



def videoGrabber(quality=0.8, size=(800,600), init_delay=100, showVideo=True):
  """Returns a video grabber object that saves images from your webcam into a PIL.Image object.
  Caveat: the returned video controller object can only be used inside the SAME cell because of sandboxing.
  
  Usage example:
    vid = videoGrabber()
    img_list = []
    for i in range(10):
      img_list.append(vid(10))
    vid(stop=True)
  """

  VIDEO_HTML = """
  <div id="video_container">
    <video autoplay
    width=%d height=%d></video>
  </div>
  <script>
  var video_div = document.getElementById("video_container");
  if(!%s){
    video_div.style.position = 'absolute';
    video_div.style.left = '-9999px';
  }
  var video = document.querySelector('video');
  var canvas = document.createElement('canvas');
  canvas.id = "canvas_container";
  var video_ready = false;
  const nav = navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
      video.srcObject = stream;
      sleep(%f).then(() => video_ready = true);
      });
  // https://stackoverflow.com/a/951057
  function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
  function getData(ms){
    if(video_ready){
    return new Promise(resolve=>{
      sleep(ms).then(() => {
        var [w,h] = [video.offsetWidth, video.offsetHeight];
        canvas.width = w;
        canvas.height = h;
        canvas.getContext('2d').drawImage(video, 0, 0, w, h);
        resolve(canvas.toDataURL('image/jpeg', %f));
        });
      })
    }
  }
  function stopVideo(){
    video.srcObject.getVideoTracks()[0].stop();
    canvas.remove();
    video.remove();
    video_div.remove();
  }
  </script>
  """
  showVideo = "true" if showVideo else "false"
  handle = display(HTML(VIDEO_HTML % (size[0],size[1],showVideo,init_delay,quality)), display_id='videoHTML')

  def videoContr(ms=10, stop=False):
    if not stop:
      while True:
        data = eval_js("getData(%s)" % str(ms))        
        if data:
          binary = b64decode(data.split(',')[1])
          f = BytesIO(binary)
          return Image.open(f)
        else:
          sleep(0.1)
    else:
      eval_js("stopVideo()")
  
  return videoContr
    
def drawbox(img, box):
  draw = ImageDraw.Draw(img)
  draw.rectangle([int(box[0]*img.size[0]),
                  int(box[1]*img.size[1]),
                  int(box[2]*img.size[0]),
                  int(box[3]*img.size[1])])
  return img

def flip(img, box):
  [x_min, y_min, x_max, y_max] = box
  img = ImageOps.flip(img)
  return img, [x_min, min([1-y_min,1-y_max]), x_max, max([1-y_min,1-y_max])]

def mirror(img, box):
  [x_min, y_min, x_max, y_max] = box
  img = ImageOps.mirror(img)
  return img, [min([1-x_min,1-x_max]), y_min, max([1-x_min,1-x_max]), y_max]

def flip_mirror(img, box):
  img, box = flip(img, box)
  img, box = mirror(img, box)
  return img, box

def rnd_solarize(img, seed=42):
  rnd = np.random.RandomState(seed)
  return ImageOps.solarize(img, threshold=rnd.randint(0,200,1))

def rnd_brightness(img, seed=42):
  rnd = np.random.RandomState(seed)
  enhancer = ImageEnhance.Brightness(img)
  return enhancer.enhance(rnd.rand())

def rnd_translate(img, box, seed=42):
  [x_min, y_min, x_max, y_max] = box
  rnd = np.random.RandomState(seed)
  x = rnd.randint(-min([x_min,x_max])*img.size[0],img.size[0]-max([x_min,x_max])*img.size[0],1)[0]
  y = rnd.randint(-min([y_min,y_max])*img.size[1],img.size[1]-max([y_min,y_max])*img.size[1],1)[0]
  img = img.transform(img.size, Image.AFFINE, (1, 0, -x, 0, 1, -y))
  x_min, y_min, x_max, y_max = x_min+x/img.size[0], y_min+y/img.size[1], x_max+x/img.size[0], y_max+y/img.size[1]
  return img, [x_min, y_min, x_max, y_max]
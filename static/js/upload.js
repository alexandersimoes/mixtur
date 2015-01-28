Dropzone.autoDiscover = false;

var dz = new Dropzone(document.body, {
    acceptedFiles: ".mp3, .png, .jpg",
    autoProcessQueue: false,
    clickable: false,
    maxFiles: 50,
    maxFilesize: 20, // in MB
    parallelUploads: 4,
    previewsContainer: "#songs-dropzone",
    previewTemplate: document.querySelector('#preview-template').innerHTML,
    sending: function(file, xhr, formData) {
      d3.select("#uploading").style("display", "flex")
      formData.append("mix_id", d3.select("input[name='mix-id']").property("value"));
      // if(!d3.select(".album-art p").empty()){
      //   formData.append("no_img", "true");
      // }
      formData.append("mix_palette", d3.select("input[name='mix-palette']").property("value"));
      formData.append("song_filesize", file.size);
      formData.append("song_artist", d3.select(file.previewElement).select("p.song-artist input").property("value"));
      formData.append("song_title", d3.select(file.previewElement).select("p.song-title input").property("value"));
      formData.append("song_num", d3.select(file.previewElement).select(".dz-num").text());
    },
    success: function(file, resp) {
        d3.select(".notify.success a").attr("href", "/m/"+resp["mix_slug"]+"/");
    },
    thumbnail: function(file, img_data) {
      d3.select(".album-art img").attr("src", img_data)
      var img = new Image();
      img.onload = function ( ) { 
        var cols = Colibri.extractImageColors(img, 'hex');
        var palette = [cols.background].concat(cols.content)
        d3.select("input[name='mix-palette']").property("value", JSON.stringify(palette))
        console.log(palette)
      };
      img.src = img_data;
    },
    thumbnailWidth: 300,
    thumbnailHeight: 300,
    uploadMultiple: false,
    url: "/uploadr/song/",
  });
//
// DropZone Events -->
//
// EVENT: an error has occured
// e.g. wrong file type or file too large (> maxfilesize)
dz.on("error", function(file, error){
  d3.select(".notify.error").style("display", "block").text(error)
  setTimeout(function(){
    d3.select(".notify.error").style("display", "none");
  }, 5000);
  d3.select(file.previewElement).remove();
})
//
// EVENT: new file is added (dropped on page)
dz.on("addedfile", function(file) {
  // Capture the Dropzone instance as closure.
  var _this = this;
  if(file.type == "image/jpeg" || file.type == "image/png"){
    d3.select(file.previewElement).remove();
    d3.select(".album-art").html('<img src="" data-dz-thumbnail />')
    var remove_link = d3.select(".album-art").append("a").attr("class", "delete dz-remove").attr("data-dz-remove", "true").html('<i title="Delete mix" class="fa fa-trash-o"></i> remove')
    remove_link.on("click", function(){
      d3.select(".album-art").html('<p>Drag album art to upload.</p>')
      _this.removeFile(file);
      d3.event.preventDefault();
    })
  }
  else if(file.type == "audio/mp3") {
    // hide the info text
    d3.select(".dropzone span.help").style("display", "none")
    // Use ID3 library to find artist and song title info from file
    ID3.loadTags(file.name, function() {
      var tags = ID3.getAllTags(file.name);
      d3.select(file.previewElement).select("p.song-title input").attr("value", tags.title)
      d3.select(file.previewElement).select("p.song-artist input").attr("value", tags.artist)
    }, { dataReader: FileAPIReader(file) });
    // set track num baesd on elements position on page
    set_track_nums();
    // set dragging events on song element
    file.previewElement.addEventListener('dragstart', handleDragStart);
    file.previewElement.addEventListener('dragend', handleDragEnd);
    file.previewElement.addEventListener('dragover', handleDragOver);
    file.previewElement.addEventListener('dragleave', handleDragLeave);
    file.previewElement.addEventListener('drop', handleDrop);
  }
});
dz.on("processing", function() {
  this.options.autoProcessQueue = true;
});
dz.on("removedfile", function(){
  // set track num baesd on elements position on page
  set_track_nums();
})
dz.on("queuecomplete", function() {
  document.body.scrollTop = document.documentElement.scrollTop = 0;
  d3.select(".notify.success").style("display", "block");
  d3.select("#upload").text("Update");
})

d3.select("#upload").on("click", function(){
  // update DB with palette for randomly tinted default img
  var mix_id = d3.select("input[name='mix-id']").property("value");
  var mix_title = d3.select("input[name='mix-title']").property("value");
  var mix_desc = d3.select("textarea").property("value");
  d3.xhr("/uploadr/song/",function(error, data) {
      data = JSON.parse(data.response);
      if(data["mix_id"]){
        d3.select(".notify.success a").attr("href", "/m/"+data["mix_slug"]+"/");
        d3.select("input[name='mix-id']").property("value", data["mix_id"])
        dz.processQueue(); //processes the queue
      }
    })
    .header("Content-type", "application/x-www-form-urlencoded")
    .send("POST", "mix_id="+mix_id+"&mix_title="+mix_title+"&mix_desc="+mix_desc);
  d3.event.preventDefault();
})

var userNodes, currentlyDraggedNode;
function handleDragStart(e) {
  dz.element = "";
  e.dataTransfer.setData("Text", "draggedUser: " + this.innerHTML);
  currentlyDraggedNode = this;
}
function handleDragEnd(e) {
  dz.element = document.body;
  d3.selectAll('[draggable=true]').style("border", "none");
  set_track_nums();
}

function handleDragOver(e) {
  // if(!e.dataTransfer.getData("Text")) return;
  var coords = DragDropHelpers.getEventCoords(e);
  d3.selectAll('[draggable=true]').style("border", "none")
  if(isAbove(this, coords)){
    d3.select(this).style("border-top", "dashed 2px black")
  }
  else {
    d3.select(this).style("border-bottom", "dashed 2px black")
  }
}
function handleDragLeave(e) {
  d3.select(this).style("border", "none")
}
function handleDrop(e) {
  if(!e.dataTransfer.getData("Text")) return;
  if(isAbove(this, DragDropHelpers.getEventCoords(e))){
    this.parentNode.insertBefore(currentlyDraggedNode, this)
  }
  else {
    this.parentNode.insertBefore(currentlyDraggedNode, this.nextSibling)
  }
  handleDragEnd(e);
}
function isAbove(node, coords){
  var flip_point = node.getBoundingClientRect().bottom + (node.getBoundingClientRect().height/2)
  // console.log(coords.y, flip_point)
  if(coords.y > flip_point){
    return false;
  }
  return true;
}

function set_track_nums(){
  var nums = [].slice.call(document.querySelectorAll(".dz-num"));
  nums.forEach(function(n, i){
    d3.select(n).text(i)
  })
}
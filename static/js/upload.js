  var Colibri=function(){var floor=function(n){return Math.floor(n)};var abs=function(n){return Math.abs(n)};var sqrt=function(n){return Math.sqrt(n)};var pow=function(n){return Math.pow(n,2)};var filters={hex:function(color){var hexComponent=function(n){var value=Math.floor(255*n).toString(16);return value.length===1?"0"+value:value};return"#"+color.map(hexComponent).join("")},css:function(color){return"rgb("+color.map(function(n){return Math.floor(255*n)}).join(",")+")"}};var rgbToYuv=function(rgb){return[rgb[0]*.299+rgb[1]*.587+rgb[2]*.114,rgb[0]*-.147+rgb[1]*.289+rgb[2]*.436,rgb[0]*.615+rgb[1]*.515+rgb[2]*.1]};var colorDistance=function(rgb1,rgb2){var yuv1=rgbToYuv(rgb1),yuv2=rgbToYuv(rgb2);return sqrt(pow(yuv1[0]-yuv2[0])+pow(yuv1[1]-yuv2[1])+pow(yuv1[2]-yuv2[2]))};var colorBrightness=function(rgb){return sqrt(pow(rgb[0])*.241+pow(rgb[1])*.691+pow(rgb[2])*.068)};var gatherSimilarElements=function(list,comparator){var subsets=[];for(var u=0,U=list.length;u<U;++u){var element=list[u];var closest=null;for(var v=0,V=subsets.length;v<V;++v)if(comparator(subsets[v][0],element))break;if(v===V){closest=[];subsets.push(closest)}else{closest=subsets[v]}closest.push(element)}return subsets};var meanColor=function(colorList){var finalColor=[0,0,0];for(var t=0,T=colorList.length;t<T;++t){var color=colorList[t];finalColor[0]+=color[0];finalColor[1]+=color[1];finalColor[2]+=color[2]}finalColor[0]/=colorList.length;finalColor[1]/=colorList.length;finalColor[2]/=colorList.length;return finalColor};var dominantColor=function(colorList,treshold,count){if(typeof treshold==="undefined")treshold=.1;if(typeof count==="undefined")count=null;var buckets=gatherSimilarElements(colorList,function(colorA,colorB){return colorDistance(colorA,colorB)<treshold}).sort(function(bucketA,bucketB){return bucketB.length-bucketA.length});var color=meanColor(buckets.shift());if(count===null)return color;if(count===-1)count=buckets.length;return buckets.slice(0,count).map(function(bucket){return meanColor(bucket)})};var createCanvas=function(){return document.createElement("canvas")};var loadDataFromContext=function(destination,context,x,y,width,height){var data=context.getImageData(x,y,width,height).data;for(var t=0,T=data.length;t<T;t+=4){destination.push([data[t+0]/255,data[t+1]/255,data[t+2]/255])}};var extractImageColors=function(image,filter){var canvas=createCanvas();var context=canvas.getContext("2d");canvas.width=image.width;canvas.height=image.height;context.drawImage(image,0,0,canvas.width,canvas.height);var borderImageData=[];loadDataFromContext(borderImageData,context,0,0,canvas.width-1,1);loadDataFromContext(borderImageData,context,canvas.width-1,0,1,canvas.height-1);loadDataFromContext(borderImageData,context,0,1,1,canvas.height-1);loadDataFromContext(borderImageData,context,1,canvas.height-1,canvas.width-1,1);var fullImageData=[];loadDataFromContext(fullImageData,context,0,0,canvas.width,canvas.height);var backgroundColor=dominantColor(borderImageData,.1);var contentColors=dominantColor(fullImageData,.1,-1).filter(function(color){return abs(colorBrightness(backgroundColor)-colorBrightness(color))>.4}).reduce(function(filteredContentColors,currentColor){var previous=filteredContentColors[filteredContentColors.length-1];if(!previous||colorDistance(previous,currentColor)>.3)filteredContentColors.push(currentColor);return filteredContentColors},[]);if(filter&&typeof filter!=="function")filter=filters[filter];if(filter){backgroundColor=filter(backgroundColor);contentColors=contentColors.map(function(color){return filter(color)})}return{background:backgroundColor,content:contentColors}};return{dominantColor:dominantColor,extractImageColors:extractImageColors}}();
  var x = '<div class="dz-preview dz-file-preview" draggable="true"> \
  <div class="dz-num">1.</div> \
  <div class="dz-details"> \
    <p class="song-title"> \
      <label for="song-title">Title</label> \
      <input type="text" name="song-title"></input> \
    </p> \
    <p class="song-artist"> \
      <label for="song-artist">Artist</label> \
      <input type="text" name="song-artist"></input> \
    </p> \
    <p class="song-file"> \
      <span class="file">&nbsp;</span> \
      <span class="file-info" data-dz-name></span> \
      <a href="#" class="dz-remove" data-dz-remove><i title="Delete mix" class="fa fa-trash-o"></i> remove</a> \
    </p> \
    <img data-dz-thumbnail /> \
  </div> \
</div>'
  var is_file = true;
  var leave_called = false;
  var overlay_timer = null;
  var palette;
  Dropzone.autoDiscover = false;
  var songs_drop = new Dropzone(document.body, {
      method: "POST", // can be changed to "put" if necessary
      maxFilesize: 20, // in MB
      dictDefaultMessage: "Drop songs here to upload...",
      parallelUploads: 20,
      // createImageThumbnails: false,
      previewTemplate: x,
      // paramName: "song", // The name that will be used to transfer the file
      paramName: "file",
      uploadMultiple: true, // This option will also trigger additional events (like processingmultiple).
      headers: {
        "My-Awesome-Header": "header value"
      },
      addRemoveLinks: false,
      previewsContainer: ".drop_container .dropzone",
      url: "/uploadr/song/",
      clickable: false,
      // createImageThumbnails: true,
      // maxThumbnailFilesize: 2, // in MB
      thumbnailWidth: 300,
      thumbnailHeight: 300,
      maxFiles: 30,
      acceptedFiles: ".mp3, .png, .jpg",
      autoProcessQueue: false, // When set to false you have to call myDropzone.processQueue() yourself in order to upload the dropped files.
      // forceFallback: false,
      
      dragstart: function() {
        // console.log('start drag!')
      },
      dragover: function() {
      },
      dragenter: function() {
        // console.log('enter!')
        d3.select("#drop_here").style("display", function(){ return is_file ? "flex" : "none"})
        // console.log(this)
        // console.log(a, b, c)
      },
      dragend: function() {
        // console.log('end')
      },
      dragleave: function() {
        // d3.select("#drop_here").style("display", "none")
      },
      init: function() {
        // console.log("init");
        // this.on("dragend", function(event) {
        //     alert("dragend")
        // });
      },
      canceled: function(){
        console.log('canceled!!!')
      },
      accept: function(file, done) {
        // Capture the Dropzone instance as closure.
        var _this = this;
        if(file.type.indexOf('image') > -1){
          d3.select(file.previewElement).remove();
          d3.select("#drop_here").style("display", "none")
          d3.select(".album-art").html('<img src="" data-dz-thumbnail />')
          var remove_link = d3.select(".album-art").append("a").attr("class", "delete dz-remove").attr("data-dz-remove", "true").html('<i title="Delete mix" class="fa fa-trash-o"></i> remove')
          remove_link.on("click", function(){
            d3.select(".album-art").html('<p>Drag album art here to upload.</p>')
            _this.removeFile(file);
            d3.event.preventDefault();
          })
        }
        else {
          d3.select(".dropzone span").style("display", "none")
        }
        file.previewElement.addEventListener('dragstart', handleDragStart, false);
        file.previewElement.addEventListener('dragenter', handleDragEnter, false)
        file.previewElement.addEventListener('dragover', handleDragOver, false);
        file.previewElement.addEventListener('dragleave', handleDragLeave, false);
        file.previewElement.addEventListener('drop', handleDrop, false);
        file.previewElement.addEventListener('dragend', handleDragEnd, false);
        d3.select("#drop_here").style("display", "none")
        // console.log("accept", file, done);
        console.log(d3.select(file.previewElement).select("input").node())
        d3.select(file.previewElement).selectAll("input")
          .on('focus', function(e) {
            d3.select(file.previewElement).attr("draggable", false);
          })
          .on('blur', function(e) {
            d3.select(file.previewElement).attr("draggable", true);
          })
        
        done();
      },
      thumbnail: function(a, b) {
        d3.select(".album-art img").attr("src", b)
        // console.log(b)
        var img = new Image( );
        img.onload = function ( ) { 
          var cols = Colibri.extractImageColors(img, 'hex');
          palette = [cols.background].concat(cols.content)
          console.log(palette)
        };
        img.src = b;
      },
      fallback: function() {
        // console.log("fallback");
      },
      success: function(file, resp) {
        d3.select("#uploading").style("display", "none")
        // console.log('success', resp, file.previewElement)
        if(file.type.indexOf('image') < 0){
          var artist = d3.select(file.previewElement).select("p.song-artist input").property("value")
          var title = d3.select(file.previewElement).select("p.song-title input").property("value")
          var track_num = d3.select(file.previewElement).select(".dz-num").text()
          d3.select(file.previewElement).remove()
          var track_info = d3.select(".uploaded_songs ol")
                              .append("li").attr("class", "track")
                              .append("div").attr("class", "track-info");
          track_info.append("p").attr("class", "track-num").append("span").text(track_num);
          var track_title = track_info.append("p").attr("class", "track-title");
          track_title.append("span").attr("class", "track-name").text(title)
          track_title.append("br")
          track_title.append("span").attr("class", "track-artist").text(artist)
        }
        if(!d3.select(".album-art p").empty()){
          var default_src = "/uploads/{{g.user}}/"+ resp.mix_slug +"/default_cover.jpg";
          d3.select(".album-art").html('<img src="'+default_src+'" data-dz-thumbnail />')
          var img = new Image( );
          img.onload = function ( ) { 
            var cols = Colibri.extractImageColors(img, 'hex');
            palette = [cols.background].concat(cols.content)
            palette = JSON.stringify(palette)
            
            // update DB with palette for randomly tinted default img
            d3.xhr("/uploadr/song/",function(error, data) {
                console.log(JSON.parse(data.response))
              })
              .header("Content-type", "application/x-www-form-urlencoded")
              .send("POST", "mix_id="+resp.mix_id+"&mix_palette="+palette);

          };
          img.src = default_src;
        }
      },
      successmultiple: function(file, resp) {
        console.log(file, resp)
        d3.select("#success a").attr("href", "/m/"+resp["mix_slug"]+"/");
      },
      sendingmultiple: function(files, xhr, formData) {
        d3.select("#uploading").style("display", "flex")
        formData.append("mix_id", d3.select("input[name='mix-id']").property("value"));
        formData.append("mix_title", d3.select("input[name='mix-title']").property("value"));
        formData.append("mix_desc", d3.select("textarea").property("value"));
        if(!d3.select(".album-art p").empty()){
          formData.append("no_img", "true");
        }
        if(palette){
          formData.append("mix_palette", JSON.stringify(palette));
        }
        files.forEach(function(f){
          formData.append("song_filesize", f.size);
          formData.append("song_artist", d3.select(f.previewElement).select("p.song-artist input").property("value"));
          formData.append("song_title", d3.select(f.previewElement).select("p.song-title input").property("value"));
          formData.append("song_num", d3.select(f.previewElement).select(".dz-num").text());
        })
      }
      // processing: function() {
      //   this.options.autoProcessQueue = true;
      // }
    });
  
  d3.select("#clear").on("click", function(){
    songs_drop.removeAllFiles();
    d3.event.preventDefault();
  })
  
  d3.select("#upload").on("click", function(){
    // console.log(songs_drop)
    songs_drop.processQueue(); //processes the queue
    d3.event.preventDefault();
  });
  
  
  songs_drop.on("queuecomplete", function() {
    document.body.scrollTop = document.documentElement.scrollTop = 0;
    d3.select("input#mix-title").attr("disabled", true)
    d3.select(".album-meta textarea").attr("disabled", true)
    d3.select(".actions").style("display", "none")
    d3.select("#success").style("display", "block");
    d3.selectAll(".dropzone").remove();
  })
  songs_drop.on("addedfile", function(file) {

    // var tags = ID3.getAllTags(file.name);
    // console.log(tags, file)

    ID3.loadTags(file.name, function() {
      var tags = ID3.getAllTags(file.name);
      d3.select(file.previewElement).select("p.song-title input").attr("value", tags.title)
      d3.select(file.previewElement).select("p.song-artist input").attr("value", tags.artist)
      console.log(tags)
      // console.log(tags.artist + " - " + tags.title + ", " + tags.album);
    }, {
        dataReader: FileAPIReader(file)
    });
    
    var nums = [].slice.call(document.querySelectorAll(".dz-num"));
    nums.forEach(function(n, i){
      d3.select(n).text(i+1)
    })

  });
  songs_drop.on("maxfilesreached", function(file) { console.log("maxfilesreached"); });
  songs_drop.on("maxfilesexceeded", function(file) { console.log("maxfilesexceeded"); });
  
  
  var dragSrcEl = null;
  function handleDragStart(e) {
    is_file = false;
    // Target (this) element is the source node.
    // this.style.opacity = '0.4';

    dragSrcEl = this;
    
    d3.select(dragSrcEl).select(".song-artist input").attr("value", function(){ return this.value; })
    d3.select(dragSrcEl).select(".song-title input").attr("value", function(){ return this.value; })
    d3.select(this).select(".song-artist input").attr("value", function(){ return this.value; })
    d3.select(this).select(".song-title input").attr("value", function(){ return this.value; })

    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', this.innerHTML);
  }
  function handleDragOver(e) {
    if (e.preventDefault) {
      e.preventDefault(); // Necessary. Allows us to drop.
    }

    e.dataTransfer.dropEffect = 'move';  // See the section on the DataTransfer object.

    return false;
  }
  function handleDragEnter(e) {
    // this / e.target is the current hover target.
    this.classList.add('over');
  }
  function handleDragLeave(e) {
    this.classList.remove('over');  // this / e.target is previous target element.
  }
  function handleDrop(e) {
    // this/e.target is current target element.

    if (e.stopPropagation) {
      e.stopPropagation(); // Stops some browsers from redirecting.
    }

    // Don't do anything if dropping the same column we're dragging.
    if (dragSrcEl != this) {
      // Set the source column's HTML to the HTML of the column we dropped on.

      dragSrcEl.innerHTML = this.innerHTML;
      this.innerHTML = e.dataTransfer.getData('text/html');
      
      var nums = [].slice.call(document.querySelectorAll(".dz-num"));
      nums.forEach(function(n, i){
        d3.select(n).text(i+1)
      })
    }

    return false;
  }
  function handleDragEnd(e) {
    // this/e.target is the source node.
    var cols = document.querySelectorAll('.dz-preview');
    [].forEach.call(cols, function (col) {
      col.classList.remove('over');
    });
    is_file = true;
  }

  
  var delay = (function(){
    var timer = 0;
    return function(callback, ms){
    clearTimeout (timer);
    timer = setTimeout(callback, ms);
   };
  })();
  d3.select("#mix-title").on("keyup", function(){
    var mix_title = this.value;
    delay(function(){
      var mix_id = d3.select("#mix-id").node().value;
      
      // d3.json("/uploadr/test/")
      //     .header("Content-type", "application/x-www-form-urlencoded")
      //     .post("mix_title="+mix_title+"&mix_id="+mix_id, function(error, resp) {
      //       if(error){ console.log(error); }
      //       if(resp){
      //         if(resp.mix_id){
      //           d3.select("#mix-id").attr("value", resp.mix_id);
      //           console.log(resp.mix_id)
      //         }
      //       }
      //     });


      // d3.xhr("/uploadr/test/")
      //   .post(
      //     JSON.stringify({year: "2012", customer: "type1"}),
      //     function(err, rawData){
      //         var data = JSON.parse(rawData);
      //         console.log("got response", data);
      //     }
      //   );
      // function(error, data) {
      //        console.log(error, data)
      //     })
      //    .header("Content-Type","application/json")
      //    .send("POST", JSON.stringify({"mix_title": mix_title, "mix_id": mix_id}));
      
    }, 1000 );
  })
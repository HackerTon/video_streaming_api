// jQuery(function () {
//   $("#video").on("click", function () {
//     console.log("alert clicked!");
//     alert("alert text is form");
//   });
// });

let player = videojs("video", { liveui: true, fluid: false, debug: true });
let boxes = document.getElementById("selection");
let title = document.getElementById("title");

const loader = async (response) => {
  if (!response.ok) {
    throw new Error("Not 200 response");
  }

  const datas = await response.json();

  if (datas == null) {
    // if list is empty
    let node = document.createElement("div");
    node.setAttribute(
      "class",
      "bg-blue-500 h-16 shadow-md rounded-2xl grid grid-cols place-items-center text-3xl"
    );
    node.textContent = "NO VIDEO FOUND";
    boxes.appendChild(node);

    return;
  }

  if (!datas.length) {
    // if list is empty
    let node = document.createElement("div");
    node.setAttribute(
      "class",
      "bg-white h-16 shadow-md rounded-2xl grid grid-cols place-items-center text-3xl"
    );
    node.textContent = "NO VIDEO FOUND";
    boxes.appendChild(node);

    return;
  }

  datas.forEach((element) => {
    let node = document.createElement("button");
    let titleChildNode = document.createElement("div");
    let descChildNode = document.createElement("div");
    let video = document.createElement("video");
    let videoChild = document.createElement("source");

    video.setAttribute("oncontextmenu", "return false;");
    video.appendChild(videoChild);
    video.muted = true;
    video.id = element["name"];
    video.className = "w-full";
    videoChild.src = "/getvideo/" + element["name"];
    videoChild.type = "video/mp4";
    video.load();

    node.addEventListener("mouseover", () => {
      if (!video.paused || !video.ended) {
        video.play();
      }
    });
    node.addEventListener("mouseout", () => {
      video.pause();
      video.currentTime = 0.0;
    });
    node.addEventListener("touchstart", () => {
      if (!video.paused || !video.ended) {
        video.play();
      }
    });
    node.addEventListener("touchend", () => {
      video.pause();
      video.currentTime = 0.0;
    });

    titleChildNode.className = "text-black font-bold text-lg";
    titleChildNode.textContent = element["name"];
    descChildNode.className = "text-gray-700 font-mono text-base";
    descChildNode.textContent = element["description"];
    node.className = "box";

    node.appendChild(video);
    node.appendChild(titleChildNode);
    node.appendChild(descChildNode);

    node.addEventListener("click", () => {
      // change the source by clicking
      title.textContent = element["name"];

      player.src({
        type: "application/x-mpegURL",
        src: "/videos/" + element["name"] + ".m8u3",
      });
    });
    boxes.appendChild(node);
  });
};

fetch("/list").then((response) => {
  loader(response).catch((err) => {
    // fallback to debugging host if
    // does not work
    fetch("http://localhost:5000/list").then(async (response) => {
      loader(response);
    });
  });
});

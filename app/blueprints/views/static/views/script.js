$(document).ready(function() {
    $("#add-wish").click(function() { addNewWish()});
    printWishes()
    //viewport_listener()
});

function ajaxCall(route, data, callback) {
    return $.ajax({
        method: "post",
        url: route,
        data: data,
        success: callback
    })
}

function showModal(res) {
    $("#modal-content").html(res);
    $(".typeahead__container").hide();
    $("#add-user-field").show();
    $("#modal").show();
    $(".close").click(              function() {$("#modal").hide()});
    $("#addWishUser").click(        function() {addWishUser() });
    $("#modal-left button").click(  function() {$(this).hide();$("#img_url").show()});
    $("#wishform").submit(function(event){
       ajaxCall($("#modal-right #wishform").attr("action"), {
           csrf_token: $("#csrf_token").val(),
           wish_img_url: $("#img_url").val(),
           co_wisher: $("#co_wisher").val(),
           edit_id: $("#co_wisher").val(),
           wish_title: $("#title").val(),
           quantity: $("#quantity").val(),
           wish_description: $("#description").val(),
           wish_url: $("#url").val()
       }).then(function(res){
           $("#modal").hide()
           $(res).hide().prependTo(".column:first").fadeIn({
               duration: 1500,
               start: function(){$(this).css("background-color", "#e2e2e2")},
               done: function(){$(this).css("background-color", "inherit")}
           });
       })
       event.preventDefault();
    });
    window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = "none";
            }
        }
}

function addNewWish() {
    ajaxCall("/api/wish/new", {
            csrf_token: $("#csrf_token").val(),
        }).then(function(res) {
            showModal(res)
    })
}

function printWishes() {
    ajaxCall("/api/wish/" + $("#filter").val(), {
        csrf_token: $("#csrf_token").val(),
        wish_id : 1,
        columns: 4
    }).then(function(res) {
        $(".wishes-list").empty();
        $(".wishes-list").append(res);
        $(".wish-item").click(function() { viewWish(this.id) });
    }, function(reason) {
        console.log("kunne ikke hente data, ", reason);
    });
}

function viewWish(id) {
    ajaxCall("/api/wish", {
        csrf_token: $("#csrf_token").val(),
        wish_id: id
    }).then(function(res) {
        showModal(res);
        if ($(".co_wishers_list li:first").length) {
            $(".typeahead__container").show();
            $(".co_wishers_list").show();
            $("#add-user-field").hide();
            addWishUser();
            $(".co_wishers_list a").click(function(){
                $(".co_wishers_list li[id='"+this.id+"']").remove();
            })
            $('label[for="co_wisher"]').css("visibility", "visible"); 
        }
        $(".delete-wish").click(function(){deleteWish(this.id)})
    }, function(reason) {
        console.log("kunne ikke hente data, ", reason);
    });
}

function addWishUser() {
    let co_wisher_list = [];
    ajaxCall("/api/search", { hello: "hello" }).then(function(users) {
        $("#add-user-field").hide();
        $(".typeahead__container").show();
        $('label[for="co_wisher"]').css("visibility", "visible");
        $(".js-typeahead").typeahead({
            order: "asc",
            display: "username",
            minLength: 1,
            hint: true,
            mustSelectItem: true,
            source: users,
            debug: true,
            selector:{query:"input"},
            callback: {
                onClick: function (node, a, item, event){
                    addCowisherToTypeahead(item)
                },
                onSubmit: function(node, form, item, event){
                    event.preventDefault();
                    addCowisherToTypeahead(item)
                }
            }
        });
    });
    /* FIXME: Oppdaterer co wisher list på alle ønsker i bakgrunnen også */
    function addCowisherToTypeahead(item) {
        let co_wisher = item.username;
        if (co_wisher) {
            ajaxCall("/api/cowisher", { user_id:item.id }).then(function(res){
                if(!co_wisher_list.includes(item.id)) {
                    $(".co_wishers_list").append("<li id='"+item.id+"'>" + co_wisher + ' <a id="'+item.id+'" class="delete-co-wisher">(x)</a></li>');
                    $(".co_wishers_list").show();
                    co_wisher_list.push(item.id);
                    $("#co_wisher").val(co_wisher_list);
                    console.log(co_wisher_list);
                    $(".js-typeahead").val("")
                    $(".co_wishers_list a").click(function(){
                        co_wisher_list.splice(co_wisher_list.indexOf(this.id), 1);
                        $(".co_wishers_list li[id='"+this.id+"']").remove();
                    });
                }
            }, function(reason){
                alert("Ugyldig bruker");
            });
        }
    }
}

function deleteWish(id) {
    if (confirm("Er du sikker på at du vil slette dette ønsket?") == true) {
        ajaxCall("/api/delete", { id:id }).then(function(res){
            alert(res);
            printWishes()
            $("#modal").hide();
        });
    }
}

function change600() {
    list_wishes(600);
}

function change800() {
    list_wishes(800)
}

function change801() {
    list_wishes(801)
}

function viewport_listener() {
    wishWriteModal();
    var vp800 = window.matchMedia("(max-width:800px)");
    var vp600 = window.matchMedia("(max-width:600px)");
    var vp801 = window.matchMedia("(min-width:801px)");
    if (vp600.matches) {
        list_wishes(600);
    } else if (vp800.matches) {
        list_wishes(800);
    } else {
        list_wishes(801);
    }
    vp800.addEventListener("change", change800)
    vp600.addEventListener("change", change600)
    vp801.addEventListener("change", change801)
}

function list_wishes(vp) {
    var numberOfColumns;
    if (vp == 600) {
        numberOfColumns = 1;
    } else if (vp == 800) {
        numberOfColumns = 2;
    } else if (vp == 801) {
        numberOfColumns = 4;
    }
}


function wishWriteModal(id, rw) {
    var selected_modal = rw == "r" ? "modal-r" : "modal-w";
    var modal = document.getElementById(selected_modal);
    var btn = document.getElementById("add-wish");
    var span = document.getElementsByClassName("close")[0];

    btn.onclick = function() { // Nytt ønske
        modal = document.getElementById("modal-w");
        document.getElementById("title").value = document.getElementById("title").placeholder;
        document.getElementById("description").value = document.getElementById("description").placeholder;
        document.getElementById("url").value = document.getElementById("url").placeholder;
        document.getElementById("img_url").value = document.getElementById("img_url").placeholder;
        document.getElementById("desired").checked = document.getElementById("desired").placeholder;
        document.getElementById("wish-img-w").src = "https://static.vecteezy.com/system/resources/previews/000/384/023/original/sketch-of-a-wrapped-gift-box-vector.jpg";
        document.getElementById("edit_id").value = "";
        modal.style.display = "block";
    }


    if (!isNaN(id) && rw == "w") { // Wright modal
        document.getElementById("title").value = jsonWishes[id].wish_title;
        document.getElementById("description").value = jsonWishes[id].description;
        document.getElementById("url").value = jsonWishes[id].url;
        document.getElementById("img_url").value = jsonWishes[id].img_url;
        document.getElementById("desired").checked = jsonWishes[id].desired;
        document.getElementById("wish-img-w").src = jsonWishes[id].img_url;
        document.getElementById("edit_id").value = jsonWishes[id].id;
        modal.style.display = "block";
    }

    if (!isNaN(id) && rw == "r") { // Read modal
        if (jsonWishes[id].desired) {
            document.getElementById("desired").innerHTML = "&#9733; Mest ønsket";
        }
        document.getElementById("claim_btn").style.display = jsonWishes[id].claimed == 3 ? "inherit" : "none";
        document.getElementById("unclaim_btn").style.display = jsonWishes[id].claimed == 1 ? "inherit" : "none";
        document.getElementById("wish-img-r").src = jsonWishes[id].img_url;
        document.getElementById("wish-header").innerHTML = jsonWishes[id].wish_title;
        document.getElementById("product-url").innerHTML = (new URL(jsonWishes[id].url)).hostname.replace("www.", "");
        document.getElementById("product-url").href = jsonWishes[id].url;
        document.getElementById("description").innerHTML = jsonWishes[id].description;
        document.getElementById("claimed_wish_id").value = jsonWishes[id].id;
        modal.style.display = "block";
    }
}
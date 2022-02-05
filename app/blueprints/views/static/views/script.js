$(document).ready(function() {
    requestWishes();
    $(".new-wish-button, .new-wish-button-label").click(function() { addNewWish()});
    $(".nav-checkbox").click(toggleHamburger);
    $(".logout-button").click(function(){window.location.href='/logout'}); // FIXME: statisk link
});

function ajaxCall(route, data, callback) {
    return $.ajax({
        method: "post",
        url: route,
        data: data,
        success: callback
    })
}

function toggleHamburger(){
    if ($(".nav-checkbox").is(":checked")) {
        $("main").hide(0,function(){
            $(".container").css("grid-template-columns", "1fr 0 0");
            $(".nav-toggle-item").toggle();
        })
    }
    else {
        $(".nav-toggle-item").toggle(0,function(){
            $(".container").css("grid-template-columns", "0 1fr 1fr");
            $("main").show(0)
        })
    }
}

function requestWishes() {
    ajaxCall("/api/wish/" + $("#filter").val(), {
        csrf_token: $("#csrf_token").val()
    }).then(function(wishes) {
        if (!Object.keys(wishes).length) {
            $("main").append("<h2>Ingen ønsker</h2>");
        }
        else {
            appendWishesToMain(wishes, Math.min(Math.max(Math.round($(window).width()/200),1),4));
        }
        $(window).resize(function(){
            appendWishesToMain(wishes, Math.min(Math.max(Math.round($(window).width()/200),1),4))
        })
    });
}

function appendWishesToMain(wishes, columns) {
    let current_column = 1;
    $(".wishes-list").empty()
    for (let col = 0; col < columns; col++) {
        $(".wishes-list").append('<div class="wish-column" />')
    }
    $.each(wishes, function(index, wish){
        let $div = $("<div>").attr({"class":"wish-item", "id": wish.id}).appendTo(".wish-column:nth-child("+current_column+")");
        if (wish.claimed) {
            $div.append('<div class="claimed"><i class="fa fa-check-circle claim-check-mark"></i></div>')
        }
        $div.append('<img src="'+wish.img_url+'" alt="Produktbilde av ønsket">')
        let $ul = $("<ul>").addClass("co-wisher-list list-no-style").appendTo($div);
        $ul.append('<li>'+wish.first_name+'</li>');
        $.each(wish.co_wisher, function(i, co_wisher){
            $ul.append("<li>"+co_wisher+"</li>");
        });
        $div.append('<p class="wish-item-age">' + wish.price + ' ' + wish.age + '</p>')
        let $h3 = $("<h3>").addClass("wish-item-title").appendTo($div);
        if (wish.desired) {
            $h3.append('<span>&#9733; </span>')
        }
        $h3.append(wish.title);
        if (current_column < columns) {
            current_column++;
        }
        else {
            current_column = 1;
        }
    });
    $(".wish-item").click(function() { viewWish(this.id) });
}

function showModal(res) {
    $("#modal-content").html(res);
    $(".typeahead__container").hide();
    $("#add-user-field").show();
    $("#modal").css("display", "flex");
    $(".close").click(              function() {$("#modal").hide()});
    $(".add-co-wisher-button").click(        function() {addWishUser() });
    $(".add-wish-image-from-url-button").click(  function() {$(this).hide();$("#img_url").show().select()});
    $("#wishform").submit(submitWishForm);
    window.onclick = function(event) {
            if (event.target == modal) {
                modal.style.display = "none";
            }
        }
}

function submitWishForm(event){
       ajaxCall($("#wishform").attr("action"), {
           csrf_token: $("#csrf_token").val(),
           wish_img_url: $("#img_url").val(),
           co_wisher: $("#co_wisher").val(),
           edit_id: $("#edit_id").val(),
           wish_title: $("#title").val(),
           quantity: $("#quantity").val(),
           wish_description: $("#description").val(),
           wish_url: $("#url").val(),
           price: $("#price").val(),
           desired: $("#desired").val()
       }).then(function(res){
           animateWishAdded($("#title").val())
           requestWishes();
       })
       event.preventDefault();
    }

function animateWishAdded(title) {
    $(".close, .modal-right, .modal-left fieldset").hide(800);
    let $modal = $(".modal-left");
    $modal.animate({maxWidth:"100%", width:"300px", paddingBottom: "20px", paddingTop: "50px"});
    let $h3 = $("<h3>").addClass("wish-item-title").css("padding-top", "10px").appendTo($modal);
    $h3.append(title);
    $modal.append('<p>lagt til din ønskeliste</p>');
    $(".modal-left p").css("padding-bottom", "30px");
    $modal.append('<button class="modal-btn-close-msg">Lukk</button>');
}

function addNewWish() {
    ajaxCall("/api/wish/new", {
            csrf_token: $("#csrf_token").val(),
        }).then(function(res) {
            showModal(res)
    })
}

function printWishes(columns=2) {
    ajaxCall("/api/wish/" + $("#filter").val(), {
        csrf_token: $("#csrf_token").val(),
        wish_id : 1,
        columns: columns
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
        if ($(".modal .co-wisher-list li:first").length) {
            $(".typeahead__container").show();
            $(".modal .co-wisher-list").show();
            $("#add-user-field").hide();
            $(".modal .co-wisher-list a").click(function(){
                $(".co-wishers-list li[id='"+this.id+"']").remove();
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
    ajaxCall("/api/typeahead", { hello: "hello" }).then(function(users) {
        $(".add-co-wisher-button-wrapper").hide();
        $(".typeahead__container").show();
        $(".js-typeahead").select()
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
                    $(".modal .co-wisher-list").append('<li id="'+item.id+'">'+
                        '<i id="'+item.id+'" class="fas fa-times delete-co-wisher"></i>' +
                        co_wisher + '</li>');
                    $(".modal .co-wisher-list").show();
                    co_wisher_list.push(item.id);
                    $("#co_wisher").val(co_wisher_list);
                    $(".js-typeahead").val("")
                    $(".delete-co-wisher").click(function(){
                        co_wisher_list.splice(co_wisher_list.indexOf(this.id), 1);
                        $(".modal .co-wisher-list li[id='"+this.id+"']").remove();
                    });
                }
            }, function(reason){
                alert("Ugyldig bruker");
            });
        }
    }
}

/* TODO: Fjern alert og gjør tilbakemeldingen mer sexy */
function deleteWish(id) {
    if (confirm("Er du sikker på at du vil slette dette ønsket?") == true) {
        ajaxCall("/api/delete", { id:id }).then(function(res){
            alert(res);
            printWishes()
            $("#modal").hide();
        });
    }
}
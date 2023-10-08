var currentPath;

$(document).ready(function() {
    currentPath = window.location.pathname;
    var wishRegex = /((?<=\d+)\/)?wish\/\d+/;

    if (wishRegex.test(currentPath)) {
        currentPath = currentPath.replace(wishRegex, '');
    }

    requestWishes();
    $(".new-wish-button, .new-wish-button-label").click(function() { addNewWish()});
    $(".nav-checkbox").click(toggleHamburger);
    $(".logout-button").click(function(){window.location.href='/api/logout'}); // FIXME: statisk link
    
    checkPathAndLoadWishContent();
    // Event listener to handle back button and restore modal state
    $(window).on('popstate', function () {
        checkPathAndLoadWishContent();
    });
});


function checkPathForWish() {
    var path = location.pathname;
    var regex = /\/wish\/(\d+)$/; // Regular expression to match "/wish/" followed by an integer
    var match = path.match(regex);

    if (match && match[1]) {
        return parseInt(match[1], 10);
    }
    else {
        return false
    }
}


function checkPathAndLoadWishContent() {
    var wish_id = checkPathForWish()
    if (wish_id) {
        loadWishContent(wish_id)
    }
    else {
        // Close the modal if the URL is not '/modal'
        modal.style.display = "none";
    }
}


$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrf_token);
        }
    }
});


function ajaxCallCsrf(route, data, type="POST", callback) {
    return $.ajax({
        url: route,
        type: type, // or "GET" or any other HTTP method you want to use
        data: data,
        success: callback
    });

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
    ajaxCallCsrf("/api/wish/" + $("#filter").val(), {
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
        let $icons = $("<div>").addClass("wish-icons").appendTo($div);
        if (wish.claimed) {
            $icons.append('<i class="fa fa-check-circle icon-green"></i>')
        }
        else if (wish.desired) {
            $icons.append('<i class="fa-solid fa-star icon-gold"></i>')
        }
        $div.append('<img src="'+wish.img_url+'" alt="Produktbilde av ønsket">')
        let $ul = $("<ul>").addClass("co-wisher-list list-no-style").appendTo($div);
        $ul.append('<li>'+ wish.first_name +'</li>');
        $.each(wish.co_wisher, function(i, co_wisher){
            $ul.append("<li>"+co_wisher+"</li>");
        });
        $div.append('<p class="wish-item-age">' + ((wish.price) ? 'kr. ' + wish.price + ',- / ' : "") + wish.age + '</p>')
        $div.append('<a class="wish-item-url", href="' + wish.url + '" target="_blank">' + wish.base_url + '</a>')
        let $h3 = $("<h3>").addClass("wish-item-title").appendTo($div);
        /*if (wish.desired) {
            $h3.append('<span>&#9733; </span>')
        }*/
        $h3.append(wish.title);
        if (current_column < columns) {
            current_column++;
        }
        else {
            current_column = 1;
        }
    });
    // $(".wish-item").click(function() {  });
    $(".wish-item").on("click", function(event) {
        // Check if the clicked element is not an anchor (a) tag
        if (!$(event.target).is("a")) {
            updateUrlAndLoadWishContent(this.id)
        }
    });

    $('img').on("error", function() {
        $(this).attr('src', '/static/img/gift-default.png');
    });
}


function hideModalAndUpdateUrl() {
    modal.style.display = "none";
    // Restore the original URL
    history.pushState({}, '', currentPath);
}


function showModal(res) {
    $("#modal-content").html(res);
    $(".typeahead__container").hide();
    $("#add-user-field").show();
    $("#modal").css("display", "flex");
    $(".add-co-wisher-button").click(        function() {addWishUser() });
    $(".add-wish-image-from-url-button").click(  function() {$(this).hide();$("#img_url").show().select()});
    $("#wishform").submit(submitWishForm);
    $(document).on("click", function(event) {
        if (event.target == modal || $(event.target).closest(".close").length > 0) {
            hideModalAndUpdateUrl()
        }
    });
    $('img').on("error", function() {
        $(this).attr('src', '/static/img/gift-default.png');
    });
    $("#img_url").on("change", function() {
        var newValue = $(this).val();
        $(".modal-left img").attr('src', newValue);
        console.log(newValue)
        // Perform other actions based on the new value
    });
}


function submitWishForm(event){
    let desired_val;
    if ($("#desired").is(":checked")) {
        desired_val = true;
    }

    else {
        desired_val = false;
    }
   ajaxCallCsrf($("#wishform").attr("action"), {
       csrf_token: $("#csrf_token").val(),
       wish_img_url: $("#img_url").val(),
       co_wisher: $("#co_wisher").val(),
       edit_id: $("#edit_id").val(),
       wish_title: $("#title").val(),
       quantity: $("#quantity").val(),
       wish_description: $("#description").val(),
       wish_url: $("#url").val(),
       price: $("#price").val(),
       desired: desired_val
   }).then(function(res){
       animateWishAdded($("#title").val(), $("#img_url").val())
       requestWishes();
   })
   event.preventDefault();
}


function animateWishAdded(title, img) {
    $(".close, .modal-right, .modal-left fieldset").hide(400);
    let $modal = $(".modal-left");
    $modal.animate({maxWidth:"100%", width:"300px", paddingBottom: "20px", paddingTop: "50px"});
    let $h3 = $("<h3>").addClass("wish-item-title").css("padding-top", "10px").appendTo($modal);
    $h3.append(title);
    $modal.append('<p>lagt til din ønskeliste</p>');
    $(".modal-left img").attr("src", img)
    $(".modal-left p").css("padding-bottom", "30px");
    $modal.append('<button class="modal-btn-close-msg">Lukk</button>');
    $(".modal-btn-close-msg").click(function() {hideModalAndUpdateUrl()});
}


function addNewWish() {
    ajaxCallCsrf("/api/wish/new", {
            csrf_token: $("#csrf_token").val(),
        }).then(function(res) {
            showModal(res)
            $("#url").on('input', function() { get_prisjakt_details() })
    })
}


function updateUrlAndLoadWishContent(id) {
    // Update the URL using History API
    currentPath = window.location.pathname;
    var newPath = currentPath + (currentPath.endsWith('/') ? '' : '/') + 'wish/' + id;
    history.pushState({ path: currentPath }, '', newPath);
    loadWishContent(id)
}


// Function to load modal content via AJAX
function loadWishContent(id) {
    // Make an AJAX request to fetch modal content
    $.get('/api/wish/' + id, function (data) {
        // Set modal content
        showModal(data);
        
        if ($(".modal .co-wisher-list li:first").length) {
                $(".typeahead__container").show();
                $(".modal .co-wisher-list").show();
                $("#add-user-field").hide();
                $(".modal .co-wisher-list a").click(function(){
                    $(".co-wishers-list li[id='"+this.id+"']").remove();
                })
                $('label[for="co_wisher"]').css("visibility", "visible");
        }
       
        $(".delete-wish").click( function(){deleteWish(this.id, false, "GET")} )
        $(".icon-dead-link").click( function(){ reportDeadLink(this.id) });

    })
    // .fail(function(reason) {
    //     console.log("kunne ikke hente data, ", reason);
    // });
}


function addWishUser() {
    let co_wisher_list = [];
    ajaxCallCsrf("/api/typeahead", { hello: "hello" }).then(function(users) {
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
            ajaxCallCsrf("/api/cowisher", { user_id:item.id }).then(function(res){
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


function showActionConfirmation(res, id, callback) {
    $(".confirm-action.modal-content").html(res);
    $("#modal-confirm").css("display", "flex");
    $(".button.send").click(callback);
    $(".button.abort").click(
        function() {$("#modal-confirm").hide()}
        );
    var confirmModal = document.getElementById("modal-confirm");
    window.addEventListener("click", function(event) {
        if (event.target == confirmModal) {
            confirmModal.style.display = "none";
        }
    })
}


function reportDeadLink(id, confirmed=false) {
    ajaxCallCsrf("/telegram/report-link", { id:id, confirmed:confirmed }).then(
        function(res){
            showActionConfirmation(res, id, function() {reportDeadLink(id, confirmed=true)});
        }
    )
}


function deleteWish(id, confirmed=false, method) {
    ajaxCallCsrf("/api/delete", { id:id, confirmed:confirmed }, method).then(
        function(res){
            showActionConfirmation(res, id, function() {deleteWish(id, confirmed=true, "DELETE")});
        }
    )
}


function get_prisjakt_details() {
    var productUrl = $("#url").val();

    // Regular expression pattern to match the product code in the URL
    var pattern = /https:\/\/www\.prisjakt\.no\/product\.php\?p=(\d+)/;

    // Check if the URL matches the pattern
    var matches = productUrl.match(pattern);

    if (matches) {
        var productCode = matches[1];

        // Send product code to your API using AJAX
        $.ajax({
            url: "/api/prisjakt",
            method: "POST",
            contentType: "application/json",
            data: JSON.stringify({ product_code: productCode }),
            success: function(response) {
                $("#title").val(response["product_name"])
                $("#price").val(response["product_price"])
                $("#img_url").val(response["product_image"])
                $(".modal-left img").attr("src", response["product_image"])
                $('#prisjakt-error').remove()
            },
            statusCode: {
                404: function() {
                    if (!$('#prisjakt-error').length) {
                        $("#url").after("<p id='prisjakt-error' style='font-size:0.8em;margin-top:-8px'>Fant ikke produktet hos Prisjakt, sjekk URL.</p>");
                    }
                }
            },
            error: function(xhr, status, error) {
                console.log("Error: Unable to fetch data from API: " + xhr.responseText);
            }
        });
    } else {
        $("#result").text("Invalid URL format");
    }
}

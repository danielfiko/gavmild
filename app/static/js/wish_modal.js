$("#url").on('input', function() { get_prisjakt_details() });
$("#wishform").submit(submitWishForm);
$(".typeahead__container").hide();
$("#add-user-field").show();
$(".add-co-wisher-button").click(function(){addWishUser()});
$(".add-wish-image-from-url-button").click(function() {
    $(this).hide();$("#img_url").show().select()
});
$('img').on("error", function() {
    $(this).attr('src', '/static/img/gift-default.png');
});
$("#img_url").on("change", function() {
    var newValue = $(this).val();
    $(".modal-left img").attr('src', newValue);
    // Perform other actions based on the new value
});
if ($(".modal .co-wisher-list li:first").length) {
        $(".typeahead__container").show();
        $(".modal .co-wisher-list").show();
        $("#add-user-field").hide();
        $(".modal .co-wisher-list a").click(function(){
            $(".co-wishers-list li[id='"+this.id+"']").remove();
        })
        $('label[for="co_wisher"]').css("visibility", "visible");
}

$(".delete-wish").click( function(){deleteWish(this.id)} )
$(".icon-dead-link").click( function(){ reportDeadLink(this.id) });

$("#admin-generate-image-btn").on("click", function() {
    var $btn = $(this);
    var $input = $("#admin-product-name");
    var $error = $("#admin-generate-error");
    var wishId = $input.data("wish-id");
    var productName = $input.val().trim();
    $error.hide();
    $btn.prop("disabled", true).text("Genererer...");
    $.ajax({
        url: "/api/wishes/" + wishId + "/generate-image",
        method: "POST",
        contentType: "application/json",
        data: JSON.stringify({ product_name: productName }),
    }).done(function(response) {
        $(".modal-left img").attr("src", response.img_url);
        $btn.prop("disabled", false).text("Generer");
    }).fail(function(xhr) {
        var msg = xhr.responseJSON && xhr.responseJSON.error
            ? xhr.responseJSON.error
            : "Noe gikk galt.";
        $error.text(msg).show();
        $btn.prop("disabled", false).text("Generer");
    });
});

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

function deleteWish(id) {
    loadModal("/api/delete").then(function() {
        $("#confirm-btn").one("click", function() {
            loadModal("/api/delete/" + id, "DELETE").then(function() {
                requestWishes();
            });
        });
    });
}

function reportDeadLink(id) {
    loadModal("/report-dead-link/" + id).then(function() {
        $("#confirm-btn").one("click", function() {
            loadModal("/telegram/report-link/" + id);
        });
    });
}

function submitWishForm(event){
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
       desired: $("#desired").is(":checked"),
       list_id: $("#list_id").val(), // Associate the wish with the list selected in the form.
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
    $h3.text(title);
    $modal.append('<p>lagt til din ønskeliste</p>');
    $(".modal-left img").attr("src", img)
    $(".modal-left p").css("padding-bottom", "30px");
    $modal.append('<button class="modal-btn-close-msg close-modal-btn">Lukk</button>');
    //$(".modal-btn-close-msg").click(function() {hideModalAndUpdateUrl()});
}

function addWishUser() {
    let co_wisher_list = [];
    ajaxCallCsrf("/api/typeahead", { csrf_token: $("#csrf_token").val(), searchbox: "" }).then(function(users) {
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
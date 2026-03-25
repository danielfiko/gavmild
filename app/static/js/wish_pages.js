// -----------------------------------------------------------------
// Funksjoner som brukes på sider som viser ønsker
// -----------------------------------------------------------------

let user_wishes;
$(document).ready(function() {
    if ($('.wishes-list').length) {
        requestWishes();
    }
    // Event listener to handle back button and restore modal state
    $(window).on('popstate', function () {
        checkPathAndLoadWishModal();
    });

    $("#order_by").on("change", requestWishes);

    // If the archived lists section exists on the page (own wish list page only),
    // fetch and render the user's archived lists on load.
    if ($('#archived-lists-section').length) {
        loadArchivedSection();
    }

    var lastWindowWidth = $(window).width();
    var resizeTimer;
    $(window).resize(function(){
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function(){
            var currentWidth = $(window).width();
            if (currentWidth !== lastWindowWidth) {
                lastWindowWidth = currentWidth;
                calculateColumnsAndAppendWishes(user_wishes);
            }
        }, 150);
    });

    checkPathAndLoadWishModal();
});

function checkPathAndLoadWishModal() {
    const wish_id = getWishIdFromPath();
    if (wish_id) {
        const newPath = window.location.pathname.replace(/\/wish\/\d+/, '');
        loadModal("/api/wish/" + wish_id);
    }
    else {
        closeModal();
    }
}

function getWishIdFromPath() {
    const match = location.pathname.match(/\/wish\/(\d+)$/);
    return match ? parseInt(match[1], 10) : null;
}

function requestWishes() {
    ajaxCallCsrf("/api/wish/" + $("#filter").val(), {
        csrf_token: $("#csrf_token").val(),
        order_by: $("#content-header select").val()
    }).then(function(wishes) {
        user_wishes = wishes;
        if (!Object.keys(wishes).length) {
            $("main").append("<h2>Ingen ønsker</h2>");
        }
        else {
            calculateColumnsAndAppendWishes(wishes)
        }
    });
}

// Recalculate the number of columns based on viewport width, then render.
// Accepts a specific wishes array so filtered subsets can be displayed
// without overwriting the full user_wishes cache.
function calculateColumnsAndAppendWishes(wishes) {
    appendWishesToMain(wishes, Math.min(Math.max(Math.round($(window).width()/200),1),4))
}

function appendWishesToMain(wishes, columns) {
    let current_column = 1;
    $(".wishes-list").empty()
    for (let col = 0; col < columns; col++) {
        $(".wishes-list").append('<div class="wish-column" />')
    }
    $.each(wishes, function(index, wish){
        let $div = $("<div>").attr({"class":"wish-item" + (wish.claimed ? " wish-item--claimed" : ""), "id": wish.id}).appendTo(".wish-column:nth-child("+current_column+")");
        let $icons = $("<div>").addClass("wish-icons").appendTo($div);
        if (wish.claimed) {
            $icons.append('<i class="fa fa-check-circle icon-green"></i>')
        }
        else if (wish.desired) {
            $icons.append('<i class="fa-solid fa-star icon-gold"></i>')
        }
        // Show the list name as a label beneath the URL when the wish belongs to a named list.
        // The title is HTML-escaped via a temporary span before inserting.
        if (wish.list_title) {
            $div.append('<span class="wish-list-badge">' + $('<span>').text(wish.list_title).html() + '</span>');
        }
        $div.append('<img src="'+wish.img_url+'" alt="Produktbilde av ønsket">')
        $div.find("img").on("error", function() {
            $(this).attr("src", "/static/img/gift-default.png");
        });
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
            loadModal("/api/wish/" + this.id);
        }
    });
}

// Fetch archived lists from the server and render collapsible panels in the
// archived-lists-section element (only present on the owner's own wish page).
function loadArchivedSection() {
    $.get('/api/lists', function(data) {
        var $section = $('#archived-lists-section');
        $section.empty();
        var archived = data.archived;
        if (!archived || !archived.length) {
            return;
        }
        $.each(archived, function(i, list) {
            var $item = $('<div class="archived-list-item">');
            var $title = $('<h3 class="archived-list-title">');
            $title.append($('<span>').text(list.title));
            $title.append($('<span class="list-meta">').text(' (arkivert ' + list.archived_at + ')'));
            $title.append('<i class="fa fa-chevron-down archived-list-chevron"></i>');
            var $wishContainer = $('<div class="archived-wishes-container">').hide();
            $item.append($title);
            $item.append($wishContainer);
            $section.append($item);
            $title.on('click', function() {
                if ($wishContainer.is(':visible')) {
                    $wishContainer.hide();
                    $title.find('.archived-list-chevron').css('transform', '');
                } else {
                    loadArchivedListWishes(list.id, $wishContainer);
                    $wishContainer.show();
                    $title.find('.archived-list-chevron').css('transform', 'rotate(180deg)');
                }
            });
        });
    });
}

// Fetch and render wish cards for a single archived list into $container.
function loadArchivedListWishes(list_id, $container) {
    $container.html('<p>Laster...</p>');
    $.get('/api/lists/' + list_id + '/wishes', function(wishes) {
        $container.empty();
        if (!wishes || !wishes.length) {
            $container.append('<p>Ingen ønsker i denne listen.</p>');
            return;
        }
        var $grid = $('<div class="archived-wishes-grid">');
        $.each(wishes, function(i, wish) {
            var $card = $('<div class="archived-wish-card">');
            var safeTitle = $('<span>').text(wish.title).html();
            $card.append('<img src="' + wish.img_url + '" alt="' + safeTitle + '">');
            $card.append($('<h4>').text(wish.title));
            var $btn = $('<button class="button-red button move-wish-btn">').text('Flytt ønske');
            $btn.on('click', function() { openMoveWishModal(wish.id); });
            $card.append($btn);
            $grid.append($card);
        });
        $container.append($grid);
    }).fail(function() {
        $container.html('<p>Kunne ikke laste ønsker.</p>');
    });
}

// Open the move/copy modal for a wish belonging to an archived list.
function openMoveWishModal(wish_id) {
    loadModal("/api/wishes/" + wish_id + "/move-modal").then(function() {
        var $form = $('#move-wish-form');
        // Show inline new-list fields when "Opprett ny liste" is selected in the dropdown.
        $form.find('select[name="destination_list_id"]').on('change', function() {
            $('#new-list-inline').toggle($(this).val() === 'new');
        });
        // Hide/show the date picker for the inline new list based on template choice.
        $form.find('input[name="new_list_template"]').on('change', function() {
            $('#move-new-list-date-wrapper').toggle($(this).val() === 'custom');
        });
        $form.on('submit', submitMoveWishForm);
    });
}

// Submit the move/copy form and refresh the archived section and main wish list.
function submitMoveWishForm(event) {
    event.preventDefault();
    var $form = $('#move-wish-form');
    var wish_id = $form.data('wish-id');
    var action = $form.find('input[name="move_action"]:checked').val();
    var dest_value = $form.find('select[name="destination_list_id"]').val();
    var payload = { action: action };
    if (dest_value === 'new') {
        var new_template = $form.find('input[name="new_list_template"]:checked').val();
        payload.new_list = {
            title: $('#new-list-title').val().trim(),
            template: new_template,
        };
        if (new_template === 'custom') {
            payload.new_list.expires_at = $('#move-new-list-expires').val();
        }
    } else {
        payload.destination_list_id = parseInt(dest_value, 10);
    }
    $('#move-form-error').hide();
    $.ajax({
        url: '/api/wishes/' + wish_id + '/move',
        type: 'POST',
        contentType: 'application/json',
        data: JSON.stringify(payload),
    }).done(function() {
        hideModalAndUpdateUrl();
        loadArchivedSection();
        requestWishes();
    }).fail(function(xhr) {
        var msg = xhr.responseJSON && xhr.responseJSON.error
            ? xhr.responseJSON.error
            : 'Det oppstod en feil.';
        $('#move-form-error').text(msg).show();
    });
}
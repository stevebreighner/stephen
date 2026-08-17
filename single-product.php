<?php
	namespace Framework;

	$url = get_field("url");

	if (!$url) {
		catch_404();
	}

	wp_redirect($url, 301);
	die();


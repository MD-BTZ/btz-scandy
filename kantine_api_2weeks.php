<?php
/**
 * Kantinenplan API-Integration für WordPress (2 Wochen)
 * Lädt Daten von der Scandy-API statt CSV-Datei
 */

// Konfiguration
$scandy_api_url = 'https://your-scandy-server.com/api/canteen/two_weeks';
$api_key = 'your-api-key-here'; // Optional für Sicherheit
$cache_duration = 300; // 5 Minuten Cache

// Cache-Datei
$cache_file = __DIR__ . '/canteen_2weeks_cache.json';

/**
 * Holt Daten von der Scandy-API
 */
function get_canteen_data_from_api($api_url, $api_key = null) {
    $url = $api_url;
    if ($api_key) {
        $url .= (strpos($url, '?') !== false ? '&' : '?') . 'api_key=' . urlencode($api_key);
    }
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, true);  // SSL-VERIFIKATION AKTIVIEREN!
    curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, 2);     // HOST-VERIFIKATION AKTIVIEREN!
    curl_setopt($ch, CURLOPT_USERAGENT, 'WordPress-Canteen-API/2.0');
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($http_code === 200 && $response) {
        $data = json_decode($response, true);
        if ($data && isset($data['success']) && $data['success']) {
            return $data;
        }
    }
    
    return false;
}

/**
 * Lädt gecachte Daten oder holt neue von der API
 */
function get_canteen_data($api_url, $api_key, $cache_file, $cache_duration) {
    // Prüfe Cache
    if (file_exists($cache_file)) {
        $cache_data = json_decode(file_get_contents($cache_file), true);
        if ($cache_data && isset($cache_data['timestamp'])) {
            $age = time() - $cache_data['timestamp'];
            if ($age < $cache_duration) {
                return $cache_data['data'];
            }
        }
    }
    
    // Hole neue Daten von der API
    $api_data = get_canteen_data_from_api($api_url, $api_key);
    if ($api_data) {
        // Speichere in Cache
        $cache_data = [
            'timestamp' => time(),
            'data' => $api_data
        ];
        file_put_contents($cache_file, json_encode($cache_data));
        return $api_data;
    }
    
    // Fallback: Versuche Cache auch wenn veraltet
    if (file_exists($cache_file)) {
        $cache_data = json_decode(file_get_contents($cache_file), true);
        if ($cache_data && isset($cache_data['data'])) {
            return $cache_data['data'];
        }
    }
    
    return false;
}

/**
 * Zeigt Kantinenplan-Tabelle für 2 Wochen an
 */
function display_canteen_table_2weeks($api_url, $api_key, $cache_file, $cache_duration) {
    $data = get_canteen_data($api_url, $api_key, $cache_file, $cache_duration);
    
    if (!$data || !isset($data['two_weeks'])) {
        echo '<div class="alert alert-warning">';
        echo '<strong>Hinweis:</strong> Kantinenplan-Daten konnten nicht geladen werden.';
        echo '</div>';
        return;
    }
    
    $meals = $data['two_weeks'];
    $heute = date("d.m.Y");
    $heute2 = date("j.n.Y");
    $heute3 = date("j.m.Y");
    
    // Finde heutigen Tag
    $today_index = null;
    for ($i = 0; $i < count($meals); $i++) {
        $meal_date = $meals[$i]['date'];
        $date_part = substr($meal_date, -10); // Extrahiere Datum aus "W1 - Montag, 15.01.2024"
        
        if ($heute == $date_part || $heute2 == substr($date_part, 0, -5) || $heute3 == substr($date_part, 0, -5)) {
            $today_index = $i;
            break;
        }
    }
    
    // Berechne Montag-Index für aktuelle Woche
    if ($today_index !== null && $today_index > 0) {
        $remainder = ($today_index % 5);
        if ($remainder > 0) {
            $monday_index = $today_index - $remainder;
        } else {
            $monday_index = $today_index;
        }
    } else {
        $monday_index = 0;
    }
    
    // Zeige Tabelle für 2 Wochen
    echo '<div class="canteen-plan-2weeks">';
    
    // Woche 1
    echo '<div class="week-section">';
    echo '<h3>Woche 1</h3>';
    echo '<table>';
    echo '<tr>';
    echo '<th>Tag, Datum</th>';
    echo '<th>Menü 1</th>';
    echo '<th>Menü 2 (Vegan)</th>';
    echo '</tr>';
    
    for ($i = 0; $i < 5; $i++) {
        if (isset($meals[$i])) {
            $meal = $meals[$i];
            $is_today = ($i == $today_index);
            
            $row_class = $is_today ? 'today' : '';
            
            echo '<tr' . ($row_class ? ' class="' . $row_class . '"' : '') . '>';
            echo '<td>' . htmlspecialchars($meal['date']) . '</td>';
            echo '<td>' . htmlspecialchars($meal['meat_dish']) . '</td>';
            echo '<td>' . htmlspecialchars($meal['vegan_dish']) . '</td>';
            echo '</tr>';
        }
    }
    
    echo '</table>';
    echo '</div>';
    
    // Woche 2
    echo '<div class="week-section">';
    echo '<h3>Woche 2</h3>';
    echo '<table>';
    echo '<tr>';
    echo '<th>Tag, Datum</th>';
    echo '<th>Menü 1</th>';
    echo '<th>Menü 2 (Vegan)</th>';
    echo '</tr>';
    
    for ($i = 5; $i < 10; $i++) {
        if (isset($meals[$i])) {
            $meal = $meals[$i];
            $is_today = ($i == $today_index);
            
            $row_class = $is_today ? 'today' : '';
            
            echo '<tr' . ($row_class ? ' class="' . $row_class . '"' : '') . '>';
            echo '<td>' . htmlspecialchars($meal['date']) . '</td>';
            echo '<td>' . htmlspecialchars($meal['meat_dish']) . '</td>';
            echo '<td>' . htmlspecialchars($meal['vegan_dish']) . '</td>';
            echo '</tr>';
        }
    }
    
    echo '</table>';
    echo '</div>';
    
    echo '</div>';
    
    // Zeige Cache-Info (optional)
    if (isset($data['generated_at'])) {
        echo '<div class="canteen-info" style="font-size: 0.8em; color: #666; margin-top: 10px;">';
        echo 'Aktualisiert: ' . date('d.m.Y H:i', strtotime($data['generated_at']));
        echo '</div>';
    }
}

// Verwende die Funktion
display_canteen_table_2weeks($scandy_api_url, $api_key, $cache_file, $cache_duration);
?> 
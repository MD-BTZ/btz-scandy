<?php
/**
 * Test-Version der Kantinenplan-API für WordPress
 * ISOLIERT vom Hauptsystem - nur für Tests!
 */

// Test-Konfiguration (NICHT für Produktion!)
$scandy_api_url = 'http://localhost:5000/api/canteen/current_week';
$api_key = ''; // Leer für Tests
$cache_duration = 60; // 1 Minute für Tests

// Test-Cache-Datei (separat vom Hauptsystem)
$cache_file = __DIR__ . '/test_canteen_cache.json';

// Test-Modus aktivieren
$test_mode = true;

/**
 * Test-Funktion: Zeigt Test-Informationen an
 */
function show_test_info() {
    global $scandy_api_url, $cache_file, $test_mode;
    
    echo '<div style="background: #f0f0f0; border: 2px solid #ff6b6b; padding: 10px; margin: 10px; font-family: monospace;">';
    echo '<h3>🧪 TEST-MODUS AKTIV</h3>';
    echo '<p><strong>⚠️ WARNUNG:</strong> Dies ist eine Test-Version!</p>';
    echo '<p><strong>API-URL:</strong> ' . htmlspecialchars($scandy_api_url) . '</p>';
    echo '<p><strong>Cache-Datei:</strong> ' . htmlspecialchars($cache_file) . '</p>';
    echo '<p><strong>Test-Modus:</strong> ' . ($test_mode ? 'AKTIV' : 'INAKTIV') . '</p>';
    echo '</div>';
}

/**
 * Test-Funktion: API-Verbindung testen
 */
function test_api_connection($api_url, $api_key = null) {
    echo '<div style="background: #e8f5e8; border: 2px solid #4caf50; padding: 10px; margin: 10px; font-family: monospace;">';
    echo '<h3>🔗 API-Verbindungstest</h3>';
    
    $url = $api_url;
    if ($api_key) {
        $url .= (strpos($url, '?') !== false ? '&' : '?') . 'api_key=' . urlencode($api_key);
    }
    
    echo '<p><strong>Teste URL:</strong> ' . htmlspecialchars($url) . '</p>';
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'WordPress-Canteen-Test/1.0');
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);
    
    if ($error) {
        echo '<p style="color: red;"><strong>❌ cURL-Fehler:</strong> ' . htmlspecialchars($error) . '</p>';
    } elseif ($http_code === 200) {
        echo '<p style="color: green;"><strong>✅ Verbindung erfolgreich!</strong></p>';
        echo '<p><strong>HTTP-Code:</strong> ' . $http_code . '</p>';
        
        $data = json_decode($response, true);
        if ($data && isset($data['success']) && $data['success']) {
            echo '<p style="color: green;"><strong>✅ API-Response korrekt!</strong></p>';
            echo '<p><strong>Anzahl Mahlzeiten:</strong> ' . count($data['week']) . '</p>';
        } else {
            echo '<p style="color: orange;"><strong>⚠️ API-Response unerwartet:</strong></p>';
            echo '<pre>' . htmlspecialchars(substr($response, 0, 500)) . '</pre>';
        }
    } else {
        echo '<p style="color: red;"><strong>❌ HTTP-Fehler:</strong> ' . $http_code . '</p>';
        echo '<pre>' . htmlspecialchars($response) . '</pre>';
    }
    
    echo '</div>';
}

/**
 * Test-Funktion: Cache-Test
 */
function test_cache_functionality($cache_file) {
    echo '<div style="background: #fff3cd; border: 2px solid #ffc107; padding: 10px; margin: 10px; font-family: monospace;">';
    echo '<h3>💾 Cache-Test</h3>';
    
    if (file_exists($cache_file)) {
        $cache_data = json_decode(file_get_contents($cache_file), true);
        if ($cache_data && isset($cache_data['timestamp'])) {
            $age = time() - $cache_data['timestamp'];
            echo '<p><strong>✅ Cache-Datei existiert</strong></p>';
            echo '<p><strong>Alter:</strong> ' . $age . ' Sekunden</p>';
            echo '<p><strong>Größe:</strong> ' . filesize($cache_file) . ' Bytes</p>';
            
            if (isset($cache_data['data']['week'])) {
                echo '<p><strong>Mahlzeiten im Cache:</strong> ' . count($cache_data['data']['week']) . '</p>';
            }
        } else {
            echo '<p style="color: red;"><strong>❌ Cache-Datei beschädigt</strong></p>';
        }
    } else {
        echo '<p style="color: orange;"><strong>⚠️ Cache-Datei existiert nicht</strong></p>';
    }
    
    echo '</div>';
}

/**
 * Test-Funktion: Simulierte Kantinenplan-Anzeige
 */
function show_test_canteen_table($api_url, $api_key, $cache_file, $cache_duration) {
    echo '<div style="background: #f8f9fa; border: 2px solid #007bff; padding: 10px; margin: 10px; font-family: monospace;">';
    echo '<h3>🍽️ Test-Kantinenplan</h3>';
    
    // Simuliere API-Aufruf
    $url = $api_url;
    if ($api_key) {
        $url .= (strpos($url, '?') !== false ? '&' : '?') . 'api_key=' . urlencode($api_key);
    }
    
    $ch = curl_init();
    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 10);
    curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
    curl_setopt($ch, CURLOPT_USERAGENT, 'WordPress-Canteen-Test/1.0');
    
    $response = curl_exec($ch);
    $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    curl_close($ch);
    
    if ($http_code === 200 && $response) {
        $data = json_decode($response, true);
        if ($data && isset($data['success']) && $data['success'] && isset($data['week'])) {
            
            // Speichere in Test-Cache
            $cache_data = [
                'timestamp' => time(),
                'data' => $data
            ];
            file_put_contents($cache_file, json_encode($cache_data));
            
            // Zeige Tabelle
            echo '<table style="border-collapse: collapse; width: 100%;">';
            echo '<tr style="background: #007bff; color: white;">';
            echo '<th style="border: 1px solid #ddd; padding: 8px;">Tag, Datum</th>';
            echo '<th style="border: 1px solid #ddd; padding: 8px;">Menü 1</th>';
            echo '<th style="border: 1px solid #ddd; padding: 8px;">Menü 2 (Vegan)</th>';
            echo '</tr>';
            
            foreach ($data['week'] as $meal) {
                echo '<tr style="background: #f8f9fa;">';
                echo '<td style="border: 1px solid #ddd; padding: 8px;">' . htmlspecialchars($meal['date']) . '</td>';
                echo '<td style="border: 1px solid #ddd; padding: 8px;">' . htmlspecialchars($meal['meat_dish']) . '</td>';
                echo '<td style="border: 1px solid #ddd; padding: 8px;">' . htmlspecialchars($meal['vegan_dish']) . '</td>';
                echo '</tr>';
            }
            
            echo '</table>';
            
            echo '<p style="margin-top: 10px; font-size: 0.8em; color: #666;">';
            echo '<strong>Test-Info:</strong> Daten von API geladen und in Cache gespeichert';
            echo '</p>';
            
        } else {
            echo '<p style="color: red;"><strong>❌ API-Response unerwartet</strong></p>';
            echo '<pre>' . htmlspecialchars($response) . '</pre>';
        }
    } else {
        echo '<p style="color: red;"><strong>❌ API-Aufruf fehlgeschlagen</strong></p>';
        echo '<p><strong>HTTP-Code:</strong> ' . $http_code . '</p>';
        echo '<pre>' . htmlspecialchars($response) . '</pre>';
    }
    
    echo '</div>';
}

// ===== TEST-AUSFÜHRUNG =====

// Zeige Test-Header
echo '<!DOCTYPE html>';
echo '<html><head><title>Kantinenplan API Test</title></head><body>';
echo '<h1>🧪 Kantinenplan API Test-Suite</h1>';
echo '<p><strong>⚠️ WARNUNG:</strong> Dies ist eine Test-Version! Nicht für Produktion verwenden!</p>';

// Zeige Test-Informationen
show_test_info();

// Teste API-Verbindung
test_api_connection($scandy_api_url, $api_key);

// Teste Cache-Funktionalität
test_cache_functionality($cache_file);

// Zeige Test-Kantinenplan
show_test_canteen_table($scandy_api_url, $api_key, $cache_file, $cache_duration);

// Test-Zusammenfassung
echo '<div style="background: #d1ecf1; border: 2px solid #17a2b8; padding: 10px; margin: 10px; font-family: monospace;">';
echo '<h3>📊 Test-Zusammenfassung</h3>';
echo '<p><strong>✅ API-Endpunkte getestet</strong></p>';
echo '<p><strong>✅ Cache-Mechanismus getestet</strong></p>';
echo '<p><strong>✅ WordPress-Simulation getestet</strong></p>';
echo '<p><strong>📁 Test-Cache-Datei:</strong> ' . htmlspecialchars($cache_file) . '</p>';
echo '<p><strong>🔗 API-URL:</strong> ' . htmlspecialchars($scandy_api_url) . '</p>';
echo '</div>';

echo '</body></html>';
?> 
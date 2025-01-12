<?php
if ($_SERVER["REQUEST_METHOD"] == "POST") {
    // Obtendo os dados do formulário
    $convidados = $_POST['convidados']; // Array de convidados
    $presenca = $_POST['presenca']; // Presença (sim ou não)

    // Conexão com o banco de dados (exemplo)
    $conn = new mysqli("localhost", "usuario", "senha", "banco_de_dados");

    if ($conn->connect_error) {
        die("Erro na conexão: " . $conn->connect_error);
    }

    // Inserindo os dados no banco de dados
    foreach ($convidados as $convidado) {
        $sql = "INSERT INTO confirmacoes (nome, presenca) VALUES ('$convidado', '$presenca')";

        if ($conn->query($sql) === TRUE) {
            echo "Presença confirmada para: $convidado<br>";
        } else {
            echo "Erro ao confirmar presença para: $convidado<br>";
        }
    }

    $conn->close();
}
?>

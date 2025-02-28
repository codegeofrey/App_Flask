// Función para actualizar la fecha y hora actual
function actualizarFechaHora() {
    const ahora = new Date();
    const opciones = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    };
    document.getElementById('datetime').textContent = ahora.toLocaleDateString('es-ES', opciones);
}

// Ejecutar cuando el DOM esté completamente cargado
document.addEventListener('DOMContentLoaded', function() {
    // Actualizar la fecha y hora al cargar la página
    actualizarFechaHora();
    
    // Actualizar cada segundo
    setInterval(actualizarFechaHora, 1000);
    
    // Manejar el envío del formulario
    document.getElementById('requerimiento-form').addEventListener('submit', function(e) {
        e.preventDefault();
        
        const asunto = document.getElementById('asunto').value;
        const perfil = document.getElementById('perfil').value;
        const mensaje = document.getElementById('mensaje').value;
        const fechaHora = document.getElementById('datetime').textContent;
        
        // Aquí puedes implementar la lógica para enviar los datos
        console.log('Requerimiento enviado:');
        console.log('Asunto:', asunto);
        console.log('Perfil:', perfil);
        console.log('Mensaje:', mensaje);
        console.log('Fecha y hora:', fechaHora);
        
        alert('Requerimiento enviado correctamente');
        this.reset();
    });
});
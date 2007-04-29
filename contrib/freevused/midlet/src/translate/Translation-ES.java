package translate;

import java.util.Hashtable;

public abstract class Translation {

	protected static Hashtable items;

	protected Translation() {

		items = new Hashtable();

		//ControlForm.java
	    items.put("Press any key to control", "Pulsa una tecla");
		items.put("Exit", "Salir");
		items.put("Numeric", "N�merico");
		items.put("Numeric keys", "Teclado num�rico");
		items.put("More", "M�s");
		items.put("More actions", "M�s acciones");
		items.put("Text", "Texto");
		items.put("Send text", "Enviar texto");
		items.put("Browse", "Men�");
		items.put("Browse menu", "Navegar men�");
		items.put("Get data", "Info");
		items.put("Get item data", "Cargar info");

		//NumericForm.java
	    items.put("Main", "Principal");
	    items.put("Main actions", "Acciones principales");

		//SearchForm.java
	    items.put("Connect", "Conectar");
		
	    items.put("Search", "Buscar");
	    items.put("Searching for devices...", "Buscando dispositivos");
	    items.put("Error - stopped", "Error - parado");
	    items.put("device. Searching...", "dispositivo. Buscando...");
	    items.put("devices. Searching...", "dispositivos. Buscando...");
	    items.put("Freevused server found. Searching...", "Servidor Freevused encontrado. Buscando...");
	    items.put("Done.", "Hecho.");
	    items.put("Retrieving service list...", "Descargando servicios...");

		//BrowseForm.java
	    items.put("Up menu", "Arriba");
	    items.put("Submenu", "Submen�");
	    items.put("Options submenu", "Submen� de opciones");
	    items.put("Refresh", "Refrescar");
	    items.put("Refresh menu", "Refrescar men�");

		//TextForm.java
	    items.put("Send", "Enviar");
	    items.put("Send text to Freevo", "Enviar texto a Freevo");
	    items.put("Send this to Freevo", "Enviar esto a Freevo");

	}

}

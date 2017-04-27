The Device Code

# The main code which runs the device
wsd.py
    # initialises the GUI, creates an ID, initialises data array
    ws_init()
    # processes the data and adds it to the database
    main()

# This module initialises the display and the gauge
wsinitd.py
    # Generates unique patient ID
    gen_id()
    # Initializes the data file iD.csv
    init_file(iD)
    # Initializes the strain gauge
    init_scale()
    # quits the code
    quit(root)
    # Shows the graph on the device
    show_graph(root)
    # Shows the table on the device
    show_table(root)
    # Initialises the patient upon restart
    new_patient()
    # Initialises the session upon restart
    set_reset()
    # Displays the patient iD initially
    init_disp(ID)

# This module is used when the code is in the main loop
    wsinloopd.py
    # Returns mass reading from strain gauge
    get_reading(hx, m, c)
    # Saves data to file
    save_data(time, vol, last, new, cumul, status, fname)
    # Fills the table headers
    generate_table(table_data, table)
    # Fills the table cells
    generate_graph(graph_data, graph)




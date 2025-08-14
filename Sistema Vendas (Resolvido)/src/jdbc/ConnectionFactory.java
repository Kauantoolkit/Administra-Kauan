/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package jdbc;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

/**
 *
 * @author Tampelini
 */
public class ConnectionFactory {
    
    private final String ip = "127.0.0.1";
    private final String port = "3306";
    private final String user = "root";
    private final String pass = "****";
    private final String bd = "BDVENDAS";

    public Connection getConnection() {

        try {

            return DriverManager.getConnection("jdbc:mysql://" + ip + ":" + port + "/" + bd, user, pass);

        } catch (SQLException erro) {
            System.err.println(erro);
            throw new RuntimeException(erro);
        }

    }

}

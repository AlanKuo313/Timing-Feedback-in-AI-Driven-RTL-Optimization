// Highest set input bit has priority. index = 0 when valid is 0.
module priority_encoder16 (
    input wire clk,
    input wire [15:0] req,
    output reg valid,
    output reg [3:0] index
);
    reg [15:0] req_reg;
    always @(posedge clk) begin
        req_reg <= req;
        valid <= |req_reg;
        if      (req_reg[15]) index <= 4'd15;
        else if (req_reg[14]) index <= 4'd14;
        else if (req_reg[13]) index <= 4'd13;
        else if (req_reg[12]) index <= 4'd12;
        else if (req_reg[11]) index <= 4'd11;
        else if (req_reg[10]) index <= 4'd10;
        else if (req_reg[9])  index <= 4'd9;
        else if (req_reg[8])  index <= 4'd8;
        else if (req_reg[7])  index <= 4'd7;
        else if (req_reg[6])  index <= 4'd6;
        else if (req_reg[5])  index <= 4'd5;
        else if (req_reg[4])  index <= 4'd4;
        else if (req_reg[3])  index <= 4'd3;
        else if (req_reg[2])  index <= 4'd2;
        else if (req_reg[1])  index <= 4'd1;
        else                  index <= 4'd0;
    end
endmodule
